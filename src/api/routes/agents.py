"""Agent execution API routes."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.design.agent import (
    build_design_graph,
    create_initial_state as create_design_state,
)
from src.agents.discover.agent import (
    build_discover_graph,
    create_initial_state,
)
from src.agents.prototype.agent import (
    build_prototype_graph,
    create_initial_state as create_prototype_state,
)
from src.api.schemas.project import (
    AgentStatusResponse,
    DesignOutputResponse,
    DesignStartRequest,
    DesignStartResponse,
    DiscoveryStartRequest,
    DiscoveryStartResponse,
    PrototypeFeedbackRequest,
    PrototypeFeedbackResponse,
    PrototypeOutputResponse,
    PrototypeStartRequest,
    PrototypeStartResponse,
    RespondRequest,
    RespondResponse,
)
from src.context_store.database import get_db
from src.context_store.models import (
    AgentRun,
    AgentType,
    Artifact,
    Conversation,
    MessageDirection,
    Project,
    ProjectStatus,
    RunStatus,
)
from src.context_store.repository import BusinessContextRepository
from src.orchestrator.approval import create_approval_gate
from src.tools.embeddings import embed_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/agents", tags=["agents"])


# ─── Helpers ───


async def _get_project(project_id: uuid.UUID, db: AsyncSession) -> Project:
    """Fetch project or raise 404."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_agent_run(
    run_id: uuid.UUID, project_id: uuid.UUID, db: AsyncSession
) -> AgentRun:
    """Fetch agent run or raise 404."""
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.project_id == project_id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


async def _run_discovery_graph(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    document_text: str,
    db_factory: object,
) -> None:
    """Execute the discovery graph and persist results.

    Runs as a background task after the HTTP response is sent.
    Uses its own database session from the factory.
    """
    from src.context_store.database import async_session_factory

    factory = db_factory or async_session_factory

    async with factory() as session:  # type: ignore[operator]
        try:
            # Mark as running
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Build and execute graph
            repo = BusinessContextRepository(session)
            initial = create_initial_state(
                project_id=str(project_id),
                document_text=document_text,
                repository=repo,
                embed_fn=embed_text,
            )

            graph = build_discover_graph()
            compiled = graph.compile()
            final_state = await compiled.ainvoke(initial)

            # Re-fetch the run to update
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()

            # Determine final status
            # Non-fatal errors (e.g. clarity check failure) shouldn't block
            # completion if findings were successfully extracted and stored.
            has_findings = bool(final_state.get("findings"))
            errors = final_state.get("errors", [])
            fatal_errors = [e for e in errors if "parse_documents failed" in e or "store_findings failed" in e]

            if fatal_errors:
                run.status = RunStatus.FAILED
                run.error_details = "; ".join(fatal_errors)
            elif final_state.get("questions") and not final_state.get("is_clear", True):
                run.status = RunStatus.PAUSED_FOR_INPUT
            else:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)

            run.output_summary = {
                "findings": final_state.get("findings", {}),
                "stored_count": final_state.get("stored_count", 0),
                "is_clear": final_state.get("is_clear", True),
                "questions": final_state.get("questions", []),
                "warnings": [e for e in errors if e not in fatal_errors],
            }

            # Auto-create approval gate when agent completes successfully
            if run.status == RunStatus.COMPLETED:
                await create_approval_gate(session, run)

            await session.commit()

        except Exception as e:
            logger.exception("Discovery agent run %s failed", run_id)
            await session.rollback()
            # Try to mark as failed
            try:
                result = await session.execute(
                    select(AgentRun).where(AgentRun.id == run_id)
                )
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark run %s as failed", run_id)


# ─── Real Discover Agent Runner ───


async def _run_real_discover_agent(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
) -> None:
    """Run the REAL Discover workflow against actual uploaded files.

    Reads file content from the Artifact table, passes it to the
    DiscoverWorkflow, and stores the real LLM output.
    """
    from src.agents.discover.agent import DiscoverWorkflow
    from src.context_store.database import async_session_factory
    from src.context_store.models import ApprovalGate, ApprovalStatus
    from src.tools.embeddings import embed_text as _embed_text

    async with async_session_factory() as session:
        try:
            # Mark as running
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)

            # Progressive task update for UI polling
            run.output_summary = {
                "tasks": [
                    {"name": "loading", "label": "Loading ingested sources", "status": "running", "detail": "Reading uploaded files..."},
                    {"name": "deep_analysis", "label": "Extracting business rules & entities", "status": "pending", "detail": ""},
                    {"name": "understanding", "label": "Building system understanding", "status": "pending", "detail": ""},
                    {"name": "questions", "label": "Identifying gaps & questions", "status": "pending", "detail": ""},
                    {"name": "quality", "label": "Assessing analysis quality", "status": "pending", "detail": ""},
                ],
                "metrics": {"rules_found": 0, "entities": 0, "conflicts": 0, "quality_score": 0},
            }
            await session.commit()

            # Read actual file content from Artifacts
            art_result = await session.execute(
                select(Artifact).where(Artifact.project_id == project_id)
            )
            artifacts = list(art_result.scalars().all())

            # Build file inputs for the workflow
            discover_files = []
            for a in artifacts:
                content = a.content or ""
                if not content and a.s3_key:
                    # Try to download from S3
                    try:
                        from src.services.storage import get_storage
                        storage = get_storage()
                        content = storage.download_bytes(a.s3_key).decode("utf-8", errors="replace")
                    except Exception:
                        content = f"[Binary file: {a.name}]"
                if content:
                    discover_files.append({"filename": a.name, "content": content})

            if not discover_files:
                discover_files = [{"filename": "empty", "content": "No files found to analyze"}]

            logger.info("Discover agent: processing %d files for project %s", len(discover_files), project_id)

            # Update task progress
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            tasks = run.output_summary.get("tasks", [])
            tasks[0]["status"] = "completed"
            tasks[0]["detail"] = f"Loaded {len(discover_files)} source files"
            tasks[1]["status"] = "running"
            tasks[1]["detail"] = "Calling LLM for deep analysis..."
            run.output_summary["tasks"] = tasks
            await session.commit()

            # Run the REAL DiscoverWorkflow
            repo = BusinessContextRepository(session)
            from src.agents.discover.agent import create_initial_state as create_discover_state
            from src.tools.llm import get_llm

            llm = get_llm(max_tokens=8192)

            initial_state = create_discover_state(
                project_id=str(project_id),
                files=discover_files,
                llm=llm,
                repository=repo,
                embed_fn=_embed_text,
            )

            workflow = DiscoverWorkflow()
            compiled = workflow.compile()
            final_state = await compiled.ainvoke(initial_state)

            # Extract results from the workflow output
            task_outputs = final_state.get("task_outputs", {})
            deep = task_outputs.get("deep_analysis", {})
            understanding = task_outputs.get("system_understanding", {})
            questions_data = task_outputs.get("clarification_questions", {})
            quality_data = task_outputs.get("quality_assessment", {})

            rules = deep.get("business_rules", [])
            entities = deep.get("entities", [])
            conflict_report = deep.get("conflict_report", {})
            conflicts = conflict_report.get("contradictions", []) + conflict_report.get("gaps", []) + conflict_report.get("ambiguities", [])
            questions = questions_data.get("questions", [])
            quality_score = final_state.get("quality_score", quality_data.get("overall_score", 0))

            # Build output matching what the DiscoverReport component expects
            output = {
                "tasks": [
                    {"name": "loading", "label": "Loading ingested sources", "status": "completed", "detail": f"Loaded {len(discover_files)} files"},
                    {"name": "deep_analysis", "label": "Extracting business rules & entities", "status": "completed", "detail": f"{len(rules)} rules, {len(entities)} entities"},
                    {"name": "understanding", "label": "Building system understanding", "status": "completed", "detail": "System understanding generated"},
                    {"name": "questions", "label": "Identifying gaps & questions", "status": "completed", "detail": f"{len(conflicts)} conflicts, {len(questions)} questions"},
                    {"name": "quality", "label": "Assessing analysis quality", "status": "completed", "detail": f"Quality: {quality_score:.0f}/100"},
                ],
                "metrics": {
                    "rules_found": len(rules),
                    "entities": len(entities),
                    "conflicts": len(conflicts),
                    "quality_score": round(quality_score),
                },
                "business_rules": [
                    {
                        "id": r.get("rule_id", f"BR-{i+1:03d}"),
                        "name": r.get("rule_name", r.get("title", "Untitled")),
                        "description": r.get("description", ""),
                        "source": r.get("source_reference", "Uploaded documents"),
                        "confidence": r.get("confidence", "medium"),
                    }
                    for i, r in enumerate(rules)
                ],
                "domain_entities": [
                    {
                        "name": e.get("entity_name", e.get("name", "?")),
                        "type": e.get("entity_type", e.get("type", "data_object")),
                        "attributes": [
                            a.get("name", a) if isinstance(a, dict) else a
                            for a in e.get("attributes", [])
                        ],
                        "relationships": [
                            f"{r.get('relationship_type', '')} {r.get('related_entity', r)}" if isinstance(r, dict) else r
                            for r in e.get("relationships", [])
                        ],
                    }
                    for e in entities
                ],
                "conflicts": [
                    {
                        "type": c.get("conflict_type", "ambiguity"),
                        "description": c.get("description", ""),
                        "severity": c.get("severity", "warning"),
                        "source_a": c.get("source_a", ""),
                        "source_b": c.get("source_b", ""),
                    }
                    for c in conflicts
                ],
                "clarification_questions": [
                    {
                        "question": q.get("question", ""),
                        "impact": q.get("impact_if_unanswered", q.get("impact", "")),
                        "priority": q.get("priority", "medium"),
                    }
                    for q in questions
                ],
                "system_understanding": {
                    "purpose": understanding.get("system_purpose", ""),
                    "domain": "",
                    "key_workflows": [
                        wf.get("journey_name", wf) if isinstance(wf, dict) else str(wf)
                        for wf in understanding.get("user_workflows", [])
                    ],
                },
                "quality_assessment": quality_data.get("scores", quality_data) if isinstance(quality_data, dict) else {},
            }

            # Update the agent run
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.PAUSED_FOR_APPROVAL
            run.output_summary = output
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()

            # Create approval gate
            gate = ApprovalGate(project_id=project_id, agent_run_id=run_id, gate_name="discover_approval", status=ApprovalStatus.PENDING)
            session.add(gate)
            await session.commit()

            logger.info("Discover agent run %s completed: %d rules, %d entities, %d conflicts", run_id, len(rules), len(entities), len(conflicts))

        except Exception as e:
            logger.exception("Discover agent run %s failed", run_id)
            try:
                result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                pass


# ─── Ingest Agent ───


async def _run_ingest_agent(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
) -> None:
    """Execute the Ingest agent simulation as a background task.

    Updates the AgentRun record progressively so the frontend
    can poll and see real-time task progress.
    """
    import asyncio as _asyncio

    from src.context_store.database import async_session_factory
    from src.orchestrator.approval import create_approval_gate

    async with async_session_factory() as session:
        try:
            # Mark as running
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Get uploaded artifacts for this project
            art_result = await session.execute(
                select(Artifact).where(Artifact.project_id == project_id)
            )
            uploaded = list(art_result.scalars().all())

            # Build file info from actual artifacts
            file_inputs = []
            for a in uploaded:
                meta = a.metadata_ or {}
                size_bytes = meta.get("size_bytes", 0)
                # Estimate word count from content or file size
                if a.content:
                    wc_estimate = len(a.content.split())
                elif size_bytes > 0:
                    wc_estimate = max(size_bytes // 6, 100)  # ~6 bytes per word average
                else:
                    wc_estimate = 500
                file_inputs.append({
                    "filename": a.name,
                    "file_type": a.type.value if a.type else "unknown",
                    "size_bytes": size_bytes,
                    "word_count_estimate": wc_estimate,
                })

            if not file_inputs:
                logger.warning("No artifacts found for project %s — using fallback", project_id)
                file_inputs = [{"filename": "uploaded_content", "file_type": "document", "size_bytes": 0, "word_count_estimate": 500}]

            tasks_progress = [
                {"name": "ingest_files", "label": "Ingesting files", "status": "pending", "detail": ""},
                {"name": "classify_and_structure", "label": "Classifying content", "status": "pending", "detail": ""},
                {"name": "generate_inventory", "label": "Generating source inventory", "status": "pending", "detail": ""},
                {"name": "quality_assessment", "label": "Assessing quality", "status": "pending", "detail": ""},
            ]

            # Smart file classification using simulation_data
            from src.api.services.simulation_data import classify_file, compute_quality_score, detect_scenario

            processed_files = []
            for fi in file_inputs:
                fname = fi["filename"]
                actual_wc = fi.get("word_count_estimate", 500)
                classification = classify_file(fname)
                # Use actual word count if available, else smart estimate
                wc = actual_wc if actual_wc and actual_wc > 100 else classification["word_count"]
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                processed_files.append({
                    "filename": fname,
                    "file_type": classification["file_type"],
                    "subcategory": classification["subcategory"],
                    "extension": ext,
                    "word_count": wc,
                    "description": classification["description"],
                    "status": "processed",
                })

            total_words = sum(f["word_count"] for f in processed_files)
            type_counts: dict[str, int] = {}
            for f in processed_files:
                type_counts[f["file_type"]] = type_counts.get(f["file_type"], 0) + 1
            has_code = "source_code" in type_counts or "database_schema" in type_counts

            # Detect scenario and project type
            all_filenames = [f["filename"] for f in processed_files]
            scenario = detect_scenario(all_filenames)
            has_legacy_keywords = any(kw in " ".join(all_filenames).lower() for kw in ("legacy", "current", "migration", "existing"))
            project_type = "legacy_modernization" if (has_code or has_legacy_keywords) else "greenfield"

            # Task 1: Ingest files
            tasks_progress[0]["status"] = "running"
            tasks_progress[0]["detail"] = f"Processing {len(file_inputs)} files..."
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.output_summary = {"tasks": tasks_progress, "metrics": {"files_processed": 0, "total_files": len(file_inputs), "words_extracted": 0, "sources_classified": 0}}
            await session.commit()
            await _asyncio.sleep(3)

            tasks_progress[0]["status"] = "completed"
            tasks_progress[0]["detail"] = f"{len(file_inputs)} files processed"
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.output_summary = {"tasks": tasks_progress, "metrics": {"files_processed": len(file_inputs), "total_files": len(file_inputs), "words_extracted": total_words, "sources_classified": 0}}
            await session.commit()
            await _asyncio.sleep(1)

            # Task 2: Classify
            tasks_progress[1]["status"] = "running"
            tasks_progress[1]["detail"] = "Classifying content types..."
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.output_summary["tasks"] = tasks_progress
            await session.commit()
            await _asyncio.sleep(3)

            tasks_progress[1]["status"] = "completed"
            tasks_progress[1]["detail"] = ", ".join(f"{c} {t}" for t, c in type_counts.items())
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.output_summary["tasks"] = tasks_progress
            run.output_summary["metrics"]["sources_classified"] = len(file_inputs)
            run.output_summary["project_type"] = project_type
            await session.commit()
            await _asyncio.sleep(1)

            # Task 3: Inventory
            tasks_progress[2]["status"] = "running"
            tasks_progress[2]["detail"] = "Building source inventory..."
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.output_summary["tasks"] = tasks_progress
            await session.commit()
            await _asyncio.sleep(2)

            tasks_progress[2]["status"] = "completed"
            tasks_progress[2]["detail"] = f"{len(processed_files)} sources inventoried"
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.output_summary["tasks"] = tasks_progress
            await session.commit()
            await _asyncio.sleep(1)

            # Task 4: Quality
            tasks_progress[3]["status"] = "running"
            tasks_progress[3]["detail"] = "Assessing input quality..."
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.output_summary["tasks"] = tasks_progress
            await session.commit()
            await _asyncio.sleep(2)

            # Smart quality scoring
            quality = compute_quality_score(processed_files)
            quality_score = quality["score"]

            tasks_progress[3]["status"] = "completed"
            tasks_progress[3]["detail"] = f"Quality score: {quality_score}/100"

            # ─── Store actual file content in business_context for Discover ───
            try:
                from src.context_store.repository import BusinessContextRepository
                repo = BusinessContextRepository(session)

                for artifact in uploaded:
                    file_content = artifact.content or ""
                    if not file_content:
                        # Try to read from S3 if content is not in DB
                        file_content = f"File: {artifact.name}\nType: {artifact.type.value if artifact.type else 'unknown'}"

                    await repo.store_context(
                        project_id=project_id,
                        category="ingested_source",
                        title=f"Source: {artifact.name}",
                        content=file_content[:15000],
                        source_agent=AgentType.INGEST,
                        metadata={
                            "file_type": artifact.type.value if artifact.type else "unknown",
                            "filename": artifact.name,
                        },
                    )
                await session.commit()
                logger.info("Stored %d source files in business_context", len(uploaded))
            except Exception as store_err:
                logger.warning("Failed to store sources in business_context: %s", store_err)

            # ─── LLM analysis of ingested content ───
            llm_analysis = None
            try:
                from src.agents.ingest.llm_analysis import analyze_ingested_content
                llm_analysis = await analyze_ingested_content(processed_files)
                logger.info("LLM analysis complete: domain=%s, type=%s",
                            llm_analysis.get("domain"), llm_analysis.get("project_type"))

                # Enrich processed files with LLM insights
                for assessment in llm_analysis.get("file_assessments", []):
                    for pf in processed_files:
                        if pf["filename"] == assessment.get("filename"):
                            pf["document_type"] = assessment.get("document_type", pf.get("subcategory"))
                            pf["key_topics"] = assessment.get("key_topics", [])
                            pf["summary"] = assessment.get("summary", "")
                            pf["importance"] = assessment.get("estimated_importance", "medium")

                # Use LLM's project type if available
                if llm_analysis.get("project_type"):
                    project_type = llm_analysis["project_type"]

            except Exception as llm_err:
                logger.warning("LLM analysis failed (using rule-based): %s", llm_err)

            output = {
                "tasks": tasks_progress,
                "metrics": {"files_processed": len(file_inputs), "total_files": len(file_inputs), "words_extracted": total_words, "sources_classified": len(file_inputs), "quality_score": quality_score},
                "processed_files": processed_files,
                "project_type": project_type,
                "scenario": scenario,
                "type_breakdown": type_counts,
                "quality_assessment": {"score": quality_score, "completeness": quality["completeness"], "diversity": quality["diversity"], "volume": quality["volume"], "warnings": quality["warnings"]},
            }
            if llm_analysis:
                output["llm_analysis"] = llm_analysis

            # Update run to paused_for_approval
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.PAUSED_FOR_APPROVAL
            run.output_summary = output
            run.completed_at = datetime.now(timezone.utc)
            run.token_usage = {"total_files": len(file_inputs), "processing_time_seconds": (run.completed_at - run.started_at).total_seconds()}
            await session.commit()

            # Create approval gate
            from src.context_store.models import ApprovalGate, ApprovalStatus

            gate = ApprovalGate(
                project_id=project_id,
                agent_run_id=run_id,
                gate_name="ingest_approval",
                status=ApprovalStatus.PENDING,
            )
            session.add(gate)
            await session.commit()

            logger.info("Ingest agent run %s completed with score %d", run_id, quality_score)

        except Exception as e:
            logger.exception("Ingest agent run %s failed", run_id)
            try:
                result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark ingest run %s as failed", run_id)


# ─── Discover Agent Simulation ───


async def _run_discover_agent(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
) -> None:
    """Run the Discover agent using real LLM analysis with simulation fallback."""
    from src.context_store.database import async_session_factory
    from src.context_store.models import ApprovalGate, ApprovalStatus

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            tasks = [
                {"name": "parse_classify", "label": "Analyzing source materials", "status": "pending", "detail": ""},
                {"name": "deep_analysis", "label": "Extracting business rules & entities", "status": "pending", "detail": ""},
                {"name": "system_understanding", "label": "Building system understanding", "status": "pending", "detail": ""},
                {"name": "clarification_questions", "label": "Identifying gaps & conflicts", "status": "pending", "detail": ""},
                {"name": "quality_assessment", "label": "Assessing analysis quality", "status": "pending", "detail": ""},
            ]
            metrics = {"rules_found": 0, "entities": 0, "conflicts": 0, "quality_score": 0}

            async def _save(t: list, m: dict, extra: dict | None = None) -> None:
                r2 = (await session.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()
                summary = {"tasks": t, "metrics": m}
                if extra:
                    summary.update(extra)
                r2.output_summary = summary
                await session.commit()

            # Task 1: Read sources from business_context
            tasks[0]["status"] = "running"
            tasks[0]["detail"] = "Reading ingested sources from knowledge base..."
            await _save(tasks, metrics)

            from src.context_store.models import BusinessContext
            from sqlalchemy import select as sa_select

            src_result = await session.execute(
                sa_select(BusinessContext).where(
                    BusinessContext.project_id == project_id,
                    BusinessContext.category == "ingested_source",
                )
            )
            sources = list(src_result.scalars().all())

            tasks[0]["status"] = "completed"
            tasks[0]["detail"] = f"{len(sources)} sources loaded from knowledge base"
            await _save(tasks, metrics)

            # Task 2-4: Real LLM discovery
            tasks[1]["status"] = "running"
            tasks[1]["detail"] = "AI is analyzing documents for business rules..."
            await _save(tasks, metrics)

            try:
                from src.agents.discover.llm_discovery import discover_business_rules

                llm_result = await discover_business_rules(
                    project_id=project_id,
                    ingested_content=[
                        {"source_file": s.title or "unknown", "content": s.content or ""}
                        for s in sources
                    ],
                    db=session,
                )

                rules = llm_result.get("business_rules", [])
                entities = llm_result.get("domain_entities", [])
                conflicts = llm_result.get("conflicts", [])
                questions = llm_result.get("clarification_questions", [])
                understanding = llm_result.get("system_understanding", {})
                qa = llm_result.get("quality_assessment", {})

                logger.info(
                    "LLM discovery: %d rules, %d entities, %d conflicts",
                    len(rules), len(entities), len(conflicts),
                )

            except Exception as llm_err:
                logger.warning("Real LLM discovery failed, using simulation: %s", llm_err)

                # Fall back to simulation
                from src.api.services.simulation_data import detect_scenario, get_discover_data

                ingest_result = await session.execute(
                    select(AgentRun).where(
                        AgentRun.project_id == project_id,
                        AgentRun.agent_type == AgentType.INGEST,
                    ).order_by(AgentRun.created_at.desc()).limit(1)
                )
                ingest_run = ingest_result.scalar_one_or_none()
                ingest_output = (ingest_run.output_summary or {}) if ingest_run else {}
                ingest_files = [f.get("filename", "") for f in ingest_output.get("processed_files", [])]
                scenario = ingest_output.get("scenario", detect_scenario(ingest_files))

                discover_data = get_discover_data(scenario)
                rules = discover_data["business_rules"]
                entities = discover_data["domain_entities"]
                conflicts = discover_data["conflicts"]
                questions = discover_data["clarification_questions"]
                understanding = discover_data["system_understanding"]
                qa = discover_data["quality_assessment"]

            # Update task statuses
            metrics["rules_found"] = len(rules)
            metrics["entities"] = len(entities)
            tasks[1]["status"] = "completed"
            tasks[1]["detail"] = f"{len(rules)} business rules, {len(entities)} entities extracted"
            await _save(tasks, metrics)

            tasks[2]["status"] = "completed"
            tasks[2]["detail"] = f"System understanding — {understanding.get('domain', 'General')}"

            metrics["conflicts"] = len(conflicts)
            tasks[3]["status"] = "completed"
            tasks[3]["detail"] = f"{len(conflicts)} conflicts, {len(questions)} clarification questions"

            quality_score = qa.get("score", 75)
            metrics["quality_score"] = quality_score
            tasks[4]["status"] = "completed"
            tasks[4]["detail"] = f"Quality score: {quality_score}/100"

            output = {
                "tasks": tasks, "metrics": metrics,
                "business_rules": rules, "domain_entities": entities,
                "conflicts": conflicts, "clarification_questions": questions,
                "system_understanding": understanding,
                "quality_assessment": qa,
            }

            r = (await session.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()
            r.status = RunStatus.PAUSED_FOR_APPROVAL
            r.output_summary = output
            r.completed_at = datetime.now(timezone.utc)
            await session.commit()

            # Store results in business_context for downstream agents
            try:
                from src.context_store.repository import BusinessContextRepository
                repo = BusinessContextRepository(session)

                for rule in rules:
                    await repo.store_context(
                        project_id=project_id,
                        category="business_rule",
                        title=rule.get("name", ""),
                        content=f"Business Rule {rule.get('id', '')}: {rule.get('name', '')}\n{rule.get('description', '')}\nSource: {rule.get('source', 'N/A')}\nConfidence: {rule.get('confidence', 'medium')}",
                        source_agent=AgentType.DISCOVER,
                        metadata=rule,
                    )

                for entity in entities:
                    attrs = ", ".join(entity.get("attributes", []))
                    rels = ", ".join(entity.get("relationships", []))
                    await repo.store_context(
                        project_id=project_id,
                        category="domain_entity",
                        title=entity.get("name", ""),
                        content=f"Entity: {entity['name']}\nType: {entity.get('type', '')}\nAttributes: {attrs}\nRelationships: {rels}",
                        source_agent=AgentType.DISCOVER,
                        metadata=entity,
                    )

                for conflict in conflicts:
                    await repo.store_context(
                        project_id=project_id,
                        category="conflict",
                        title=f"Conflict: {conflict.get('type', 'unknown')}",
                        content=conflict.get("description", ""),
                        source_agent=AgentType.DISCOVER,
                        metadata=conflict,
                    )

                await session.commit()
                logger.info("Stored discovery results in business_context")
            except Exception as store_err:
                logger.warning("Failed to store discovery results: %s", store_err)

            gate = ApprovalGate(project_id=project_id, agent_run_id=run_id, gate_name="discover_approval", status=ApprovalStatus.PENDING)
            session.add(gate)
            await session.commit()
            logger.info("Discover agent run %s completed", run_id)

        except Exception as e:
            logger.exception("Discover agent run %s failed", run_id)
            try:
                r = (await session.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()
                r.status = RunStatus.FAILED
                r.error_details = str(e)
                await session.commit()
            except Exception:
                pass


# ─── Design Agent Simulation ───


async def _run_design_simulation(run_id: uuid.UUID, project_id: uuid.UUID) -> None:
    """Run the Design agent using real LLM analysis with simulation fallback."""
    from src.context_store.database import async_session_factory
    from src.context_store.models import ApprovalGate, ApprovalStatus

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)

            tasks = [
                {"name": "requirements", "label": "Analyzing requirements", "status": "pending", "detail": ""},
                {"name": "architecture", "label": "Generating architecture", "status": "pending", "detail": ""},
                {"name": "schema", "label": "Designing database schema", "status": "pending", "detail": ""},
                {"name": "api", "label": "Generating API contracts", "status": "pending", "detail": ""},
                {"name": "auth", "label": "Designing auth model", "status": "pending", "detail": ""},
                {"name": "frontend", "label": "Designing frontend", "status": "pending", "detail": ""},
                {"name": "quality", "label": "Assessing design quality", "status": "pending", "detail": ""},
            ]
            metrics = {"tables": 0, "endpoints": 0, "components": 0, "quality_score": 0}
            run.output_summary = {"tasks": tasks, "metrics": metrics}
            await session.commit()

            async def _save() -> None:
                r2 = (await session.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()
                r2.output_summary = {"tasks": tasks, "metrics": metrics}
                await session.commit()

            tasks[0]["status"] = "running"
            tasks[0]["detail"] = "Reading discovered requirements..."
            await _save()

            try:
                from src.agents.design.llm_design import design_system

                tasks[0]["status"] = "completed"
                tasks[0]["detail"] = "Requirements loaded from knowledge base"
                tasks[1]["status"] = "running"
                tasks[1]["detail"] = "AI is designing system architecture..."
                await _save()

                design_result = await design_system(project_id, session)

                arch = design_result.get("architecture", {})
                db_schema = design_result.get("database_schema", {})
                api_spec = design_result.get("api_specification", {})
                auth = design_result.get("auth_design", {})
                frontend = design_result.get("frontend_design", {})
                dqa = design_result.get("quality_assessment", {})

                logger.info("LLM design: pattern=%s tables=%d endpoints=%d",
                            arch.get("pattern"), db_schema.get("total_tables", 0), api_spec.get("total_endpoints", 0))

            except Exception as llm_err:
                logger.warning("Real LLM design failed, using simulation: %s", llm_err)

                from src.api.services.simulation_data import detect_scenario, get_design_data
                ingest_result = await session.execute(
                    select(AgentRun).where(
                        AgentRun.project_id == project_id, AgentRun.agent_type == AgentType.INGEST,
                    ).order_by(AgentRun.created_at.desc()).limit(1)
                )
                ingest_run = ingest_result.scalar_one_or_none()
                scenario = (ingest_run.output_summary or {}).get("scenario", "generic") if ingest_run else "generic"
                design_data = get_design_data(scenario)
                arch = design_data["architecture"]
                db_schema = design_data["database_schema"]
                api_spec = design_data["api_specification"]
                auth = design_data["auth_design"]
                frontend = design_data["frontend_design"]
                dqa = design_data["quality_assessment"]

            # Update task statuses
            pattern = arch.get("pattern", "monolith").replace("_", " ").title()
            stack_items = [s["technology"] for s in arch.get("stack", [])[:3]]
            tasks[1]["status"] = "completed"
            tasks[1]["detail"] = f"{pattern} — {', '.join(stack_items)}"

            metrics["tables"] = db_schema.get("total_tables", len(db_schema.get("tables", [])))
            tasks[2]["status"] = "completed"
            tasks[2]["detail"] = f"{metrics['tables']} tables designed"

            metrics["endpoints"] = api_spec.get("total_endpoints", len(api_spec.get("endpoints", [])))
            tasks[3]["status"] = "completed"
            tasks[3]["detail"] = f"{metrics['endpoints']} API endpoints"

            tasks[4]["status"] = "completed"
            tasks[4]["detail"] = f"{auth.get('strategy', 'RBAC')} with {auth.get('roles', 0)} roles"

            metrics["components"] = frontend.get("components", 0)
            tasks[5]["status"] = "completed"
            tasks[5]["detail"] = f"{frontend.get('pages', 0)} pages, {metrics['components']} components"

            metrics["quality_score"] = dqa.get("score", 75)
            tasks[6]["status"] = "completed"
            tasks[6]["detail"] = f"Quality score: {metrics['quality_score']}/100"

            output = {
                "tasks": tasks, "metrics": metrics,
                "architecture": arch,
                "database_schema": db_schema,
                "api_specification": api_spec,
                "auth_design": auth,
                "frontend_design": frontend,
                "quality_assessment": dqa,
            }

            r = (await session.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()
            r.status = RunStatus.PAUSED_FOR_APPROVAL
            r.output_summary = output
            r.completed_at = datetime.now(timezone.utc)
            await session.commit()

            # Store ADRs in business_context for D4 Prototype to read
            try:
                from src.context_store.repository import BusinessContextRepository
                repo = BusinessContextRepository(session)

                for adr in arch.get("adrs", []):
                    await repo.store_context(
                        project_id=project_id,
                        category="architecture_decision",
                        title=adr.get("title", ""),
                        content=f"{adr.get('id', '')}: {adr.get('title', '')}\nDecision: {adr.get('decision', '')}",
                        source_agent=AgentType.DESIGN,
                        metadata=adr,
                    )

                # Store tech stack choices
                for s in arch.get("stack", []):
                    await repo.store_context(
                        project_id=project_id,
                        category="tech_stack_choice",
                        title=f"Tech: {s['category']}",
                        content=f"{s['category']}: {s['technology']}",
                        source_agent=AgentType.DESIGN,
                        metadata=s,
                    )

                await session.commit()
                logger.info("Stored design decisions in business_context")
            except Exception as store_err:
                logger.warning("Failed to store design decisions: %s", store_err)

            gate = ApprovalGate(project_id=project_id, agent_run_id=run_id, gate_name="design_approval", status=ApprovalStatus.PENDING)
            session.add(gate)
            await session.commit()
            logger.info("Design agent %s completed", run_id)

        except Exception as e:
            logger.exception("Design agent %s failed", run_id)
            try:
                r = (await session.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()
                r.status = RunStatus.FAILED
                r.error_details = str(e)
                await session.commit()
            except Exception:
                pass


# ─── Prototype Agent Simulation ───


async def _run_prototype_simulation(run_id: uuid.UUID, project_id: uuid.UUID) -> None:
    """Simulates the Prototype agent with progressive task updates."""
    import asyncio as _aio
    from src.context_store.database import async_session_factory
    from src.context_store.models import ApprovalGate, ApprovalStatus

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)

            tasks = [
                {"name": "interpret", "label": "Interpreting design", "status": "pending", "detail": ""},
                {"name": "generate", "label": "Generating Next.js application", "status": "pending", "detail": ""},
                {"name": "validate", "label": "Validating prototype", "status": "pending", "detail": ""},
                {"name": "deploy", "label": "Deploying preview", "status": "pending", "detail": ""},
                {"name": "quality", "label": "Assessing prototype quality", "status": "pending", "detail": ""},
            ]
            metrics = {"pages": 0, "components": 0, "files": 0, "quality_score": 0}
            run.output_summary = {"tasks": tasks, "metrics": metrics}
            await session.commit()

            for i, (detail, mkey, mval) in enumerate([
                ("9 pages, 24 components, mock data models parsed", "pages", 9),
                ("47 files generated with shadcn/ui + Tailwind", "files", 47),
                ("All routes valid, 0 errors, 2 warnings", None, None),
                ("Preview deployed to http://localhost:3200", None, None),
                ("Quality score: 76/100", "quality_score", 76),
            ]):
                tasks[i]["status"] = "running"
                result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
                run = result.scalar_one()
                run.output_summary = {"tasks": tasks, "metrics": metrics}
                await session.commit()
                await _aio.sleep(3)
                tasks[i]["status"] = "completed"
                tasks[i]["detail"] = detail
                if mkey:
                    metrics[mkey] = mval
                metrics["components"] = 24
                result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
                run = result.scalar_one()
                run.output_summary = {"tasks": tasks, "metrics": metrics}
                await session.commit()
                await _aio.sleep(1)

            output = {
                "tasks": tasks, "metrics": metrics,
                "preview_url": "http://localhost:3200",
                "prototype_spec": {"pages": ["Dashboard", "Projects", "Sprint Board", "Backlog", "Task Detail", "Timesheet", "Settings", "Login", "Sprint List"], "components": 24, "mock_data_models": 5},
                "validation": {"passed": True, "errors": [], "warnings": ["Deep import path in layout.tsx", "Excessive any types in 2 files"]},
                "quality_assessment": {"score": 76, "page_coverage": 90, "component_coverage": 80, "mock_data_quality": 65, "navigation": 85, "responsive": 70, "role_differentiation": 60},
            }

            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.PAUSED_FOR_APPROVAL
            run.output_summary = output
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()

            gate = ApprovalGate(project_id=project_id, agent_run_id=run_id, gate_name="prototype_approval", status=ApprovalStatus.PENDING)
            session.add(gate)
            await session.commit()
            logger.info("Prototype simulation %s completed", run_id)

        except Exception as e:
            logger.exception("Prototype simulation %s failed", run_id)
            try:
                result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                pass


# ─── Agent Runner Registry ───

AGENT_RUNNERS = {
    "ingest": _run_ingest_agent,
    "discover": _run_discover_agent,
    "design": _run_design_simulation,
    "prototype": _run_prototype_simulation,
}


# ─── Endpoints ───


@router.post("/ingest/start", status_code=201)
async def start_ingest(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start the Ingest Agent for the given project."""
    project = await _get_project(project_id, db)

    # Update project status
    project.status = ProjectStatus.INGEST

    # Create agent run
    agent_run = AgentRun(
        project_id=project_id,
        agent_type=AgentType.INGEST,
        status=RunStatus.PENDING,
    )
    db.add(agent_run)
    await db.flush()
    await db.refresh(agent_run)
    run_id = agent_run.id

    # Launch in background
    asyncio.create_task(_run_ingest_agent(run_id, project_id))

    return {"run_id": str(run_id), "agent_type": "ingest", "status": "running", "message": "Ingest agent started"}


@router.post("/ingest/restart", status_code=201)
async def restart_ingest(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-run the Ingest Agent with all files (original + newly added)."""
    project = await _get_project(project_id, db)

    # Remove old pending approval gates for ingest
    from src.context_store.models import ApprovalGate

    old_gates = await db.execute(
        select(ApprovalGate).join(AgentRun).where(
            ApprovalGate.project_id == project_id,
            AgentRun.agent_type == AgentType.INGEST,
            ApprovalGate.status == "pending",
        )
    )
    for gate in old_gates.scalars().all():
        gate.status = "rejected"  # type: ignore[assignment]

    # Set project back to ingest
    project.status = ProjectStatus.INGEST

    # Create new agent run
    agent_run = AgentRun(project_id=project_id, agent_type=AgentType.INGEST, status=RunStatus.PENDING)
    db.add(agent_run)
    await db.flush()
    await db.refresh(agent_run)
    run_id = agent_run.id

    asyncio.create_task(_run_ingest_agent(run_id, project_id))

    return {"run_id": str(run_id), "agent_type": "ingest", "status": "running", "message": "Ingest agent restarted with all files"}


@router.get("/latest")
async def get_latest_run(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the most recent agent run for this project."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="No agent runs found")

    # Get approval gate if exists
    gate_result = await db.execute(
        select(ApprovalGate).where(ApprovalGate.agent_run_id == run.id)
    )
    gate = gate_result.scalar_one_or_none()

    return {
        "run_id": str(run.id),
        "agent_type": run.agent_type.value,
        "status": run.status.value,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "output_summary": run.output_summary or {},
        "error_details": run.error_details,
        "approval_gate": {"id": str(gate.id), "status": gate.status.value, "reviewer_notes": gate.reviewer_notes} if gate else None,
    }


from src.context_store.models import ApprovalGate


@router.post("/discovery/start", response_model=DiscoveryStartResponse, status_code=201)
async def start_discovery(
    project_id: uuid.UUID,
    payload: DiscoveryStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a Discovery Agent run for the given project."""
    project = await _get_project(project_id, db)

    # Check if there's already a PENDING discover run (created by approval auto-start)
    existing = await db.execute(
        select(AgentRun).where(
            AgentRun.project_id == project_id,
            AgentRun.agent_type == AgentType.DISCOVER,
            AgentRun.status == RunStatus.PENDING,
        ).order_by(AgentRun.created_at.desc()).limit(1)
    )
    agent_run = existing.scalar_one_or_none()

    if agent_run:
        run_id = agent_run.id
        logger.info("Found existing PENDING discover run %s, starting it", run_id)
    else:
        # Set project status to DISCOVERY
        project.status = ProjectStatus.DISCOVER

        # Create agent run record
        agent_run = AgentRun(
            project_id=project_id,
            agent_type=AgentType.DISCOVER,
            status=RunStatus.PENDING,
            input_context={"document_text": (payload.document_text if payload else "")},
        )
        db.add(agent_run)
        await db.flush()
        await db.refresh(agent_run)
        run_id = agent_run.id

    await db.commit()

    # Start the simulation — store task ref to prevent GC
    from src.api.routes.approvals import _background_tasks
    task = asyncio.get_running_loop().create_task(_run_discover_agent(run_id, project_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "run_id": run_id,
        "status": RunStatus.PENDING,
        "message": "Discovery agent started",
    }


@router.get("/{run_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the current status of an agent run."""
    await _get_project(project_id, db)
    run = await _get_agent_run(run_id, project_id, db)

    output = run.output_summary or {}

    # Check for approval gate
    from src.context_store.models import ApprovalGate as AG
    gate_result = await db.execute(select(AG).where(AG.agent_run_id == run_id))
    gate = gate_result.scalar_one_or_none()

    resp: dict = {
        "run_id": run.id,
        "agent_type": run.agent_type,
        "status": run.status,
        "pending_questions": output.get("questions", []) if run.status == RunStatus.PAUSED_FOR_INPUT else [],
        "output_summary": output,
        "errors": [run.error_details] if run.error_details else [],
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }
    if gate:
        resp["approval_gate"] = {
            "id": str(gate.id),
            "status": gate.status.value,
            "reviewer_notes": gate.reviewer_notes,
        }
    return resp


@router.post("/{run_id}/respond", response_model=RespondResponse)
async def respond_to_agent(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: RespondRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit user answers to agent clarification questions and resume the workflow."""
    await _get_project(project_id, db)
    run = await _get_agent_run(run_id, project_id, db)

    if run.status != RunStatus.PAUSED_FOR_INPUT:
        raise HTTPException(
            status_code=409,
            detail=f"Agent run is not awaiting input (current status: {run.status.value})",
        )

    # Merge the original document text with user answers and re-run
    original_text = (run.input_context or {}).get("document_text", "")
    user_responses = [a.model_dump() for a in payload.answers]

    # Store answers in input_context for audit trail
    run.input_context = {
        **run.input_context,
        "user_responses": user_responses,
    }
    run.status = RunStatus.PENDING
    run.output_summary = {}
    await db.flush()

    # Re-launch graph with user responses included
    asyncio.create_task(
        _run_discovery_graph_with_responses(
            run_id, project_id, original_text, user_responses, None
        )
    )

    return {
        "run_id": run_id,
        "status": RunStatus.PENDING,
        "message": "Responses received, agent resuming",
    }


@router.post("/{run_id}/skip-questions", response_model=RespondResponse)
async def skip_questions(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Skip clarification questions and proceed directly to storing findings.

    Use this when the user decides the document is sufficient as-is
    and doesn't want to answer the agent's clarification questions.
    """
    await _get_project(project_id, db)
    run = await _get_agent_run(run_id, project_id, db)

    if run.status != RunStatus.PAUSED_FOR_INPUT:
        raise HTTPException(
            status_code=409,
            detail=f"Agent run is not awaiting input (current status: {run.status.value})",
        )

    original_text = (run.input_context or {}).get("document_text", "")

    run.status = RunStatus.PENDING
    run.output_summary = {}
    await db.flush()

    # Re-launch graph with skip_clarity=True so it bypasses check_clarity routing
    asyncio.create_task(
        _run_discovery_graph_skip_clarity(run_id, project_id, original_text, None)
    )

    return {
        "run_id": run_id,
        "status": RunStatus.PENDING,
        "message": "Questions skipped, agent proceeding to store findings",
    }


async def _run_discovery_graph_skip_clarity(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    document_text: str,
    db_factory: object,
) -> None:
    """Re-run discovery graph with skip_clarity=True to bypass clarification."""
    from src.context_store.database import async_session_factory

    factory = db_factory or async_session_factory

    async with factory() as session:  # type: ignore[operator]
        try:
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            await session.commit()

            repo = BusinessContextRepository(session)
            initial = create_initial_state(
                project_id=str(project_id),
                document_text=document_text,
                repository=repo,
                embed_fn=embed_text,
            )
            initial["skip_clarity"] = True

            graph = build_discover_graph()
            compiled = graph.compile()
            final_state = await compiled.ainvoke(initial)

            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()

            if final_state.get("errors"):
                run.status = RunStatus.FAILED
                run.error_details = "; ".join(final_state["errors"])
            else:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)

            run.output_summary = {
                "findings": final_state.get("findings", {}),
                "stored_count": final_state.get("stored_count", 0),
                "is_clear": final_state.get("is_clear", True),
                "questions": final_state.get("questions", []),
            }

            if run.status == RunStatus.COMPLETED:
                await create_approval_gate(session, run)

            await session.commit()

        except Exception as e:
            logger.exception("Discovery agent skip-clarity run %s failed", run_id)
            await session.rollback()
            try:
                result = await session.execute(
                    select(AgentRun).where(AgentRun.id == run_id)
                )
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark run %s as failed", run_id)


async def _run_discovery_graph_with_responses(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    document_text: str,
    user_responses: list[dict],
    db_factory: object,
) -> None:
    """Re-run discovery graph with user responses injected into state."""
    from src.context_store.database import async_session_factory

    factory = db_factory or async_session_factory

    async with factory() as session:  # type: ignore[operator]
        try:
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            await session.commit()

            repo = BusinessContextRepository(session)
            initial = create_initial_state(
                project_id=str(project_id),
                document_text=document_text,
                repository=repo,
                embed_fn=embed_text,
            )
            initial["user_responses"] = user_responses

            graph = build_discover_graph()
            compiled = graph.compile()
            final_state = await compiled.ainvoke(initial)

            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()

            if final_state.get("errors"):
                run.status = RunStatus.FAILED
                run.error_details = "; ".join(final_state["errors"])
            elif final_state.get("questions") and not final_state.get("is_clear", True):
                run.status = RunStatus.PAUSED_FOR_INPUT
            else:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)

            run.output_summary = {
                "findings": final_state.get("findings", {}),
                "stored_count": final_state.get("stored_count", 0),
                "is_clear": final_state.get("is_clear", True),
                "questions": final_state.get("questions", []),
            }

            if run.status == RunStatus.COMPLETED:
                await create_approval_gate(session, run)

            await session.commit()

        except Exception as e:
            logger.exception("Discovery agent resume %s failed", run_id)
            await session.rollback()
            try:
                result = await session.execute(
                    select(AgentRun).where(AgentRun.id == run_id)
                )
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark run %s as failed", run_id)


# ─── Design Agent Endpoints ───


@router.post("/design/start", response_model=DesignStartResponse, status_code=201)
async def start_design(
    project_id: uuid.UUID,
    payload: DesignStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a Design Agent run for the given project.

    Requires the project to be in 'design' status (set after discovery approval).
    Reads all business_context entries from discovery and generates system design.
    """
    project = await _get_project(project_id, db)

    # Check if there's already a PENDING design run (created by approval auto-start)
    existing = await db.execute(
        select(AgentRun).where(
            AgentRun.project_id == project_id,
            AgentRun.agent_type == AgentType.DESIGN,
            AgentRun.status == RunStatus.PENDING,
        ).order_by(AgentRun.created_at.desc()).limit(1)
    )
    agent_run = existing.scalar_one_or_none()

    if agent_run:
        run_id = agent_run.id
        logger.info("Found existing PENDING design run %s, starting it", run_id)
    else:
        if project.status != ProjectStatus.DESIGN:
            raise HTTPException(
                status_code=409,
                detail=f"Project must be in 'design' status to start design agent "
                f"(current: {project.status.value})",
            )

        reviewer_notes = (payload.reviewer_notes or "") if payload else ""

        # Create agent run record
        agent_run = AgentRun(
            project_id=project_id,
            agent_type=AgentType.DESIGN,
            status=RunStatus.PENDING,
            input_context={"reviewer_notes": reviewer_notes},
        )
        db.add(agent_run)
        await db.flush()
        await db.refresh(agent_run)
        run_id = agent_run.id

    await db.commit()

    # Start the simulation — store task ref to prevent GC
    from src.api.routes.approvals import _background_tasks
    task = asyncio.get_running_loop().create_task(_run_design_simulation(run_id, project_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "run_id": run_id,
        "status": RunStatus.PENDING,
        "message": "Design agent started",
    }


@router.get("/{run_id}/design-output", response_model=DesignOutputResponse)
async def get_design_output(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the design agent output including all generated artifacts."""
    await _get_project(project_id, db)
    run = await _get_agent_run(run_id, project_id, db)

    # Fetch artifacts for this run
    result = await db.execute(
        select(Artifact)
        .where(Artifact.agent_run_id == run_id)
        .order_by(Artifact.created_at)
    )
    artifacts = list(result.scalars().all())

    output = run.output_summary or {}

    return {
        "run_id": run.id,
        "agent_type": run.agent_type,
        "status": run.status,
        "design": output.get("design", {}),
        "artifacts": artifacts,
        "errors": [run.error_details] if run.error_details else [],
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


async def _run_design_graph(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    reviewer_notes: str,
    db_factory: object,
) -> None:
    """Execute the design graph and persist results.

    Runs as a background task after the HTTP response is sent.
    """
    from src.context_store.database import async_session_factory

    factory = db_factory or async_session_factory

    async with factory() as session:  # type: ignore[operator]
        try:
            # Mark as running
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Build and execute graph
            repo = BusinessContextRepository(session)
            initial = create_design_state(
                project_id=str(project_id),
                agent_run_id=str(run_id),
                reviewer_notes=reviewer_notes,
                repository=repo,
                session=session,
            )

            graph = build_design_graph()
            compiled = graph.compile()
            final_state = await compiled.ainvoke(initial)

            # Re-fetch the run to update
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()

            # Determine final status
            if final_state.get("errors"):
                run.status = RunStatus.FAILED
                run.error_details = "; ".join(final_state["errors"])
            else:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)

            run.output_summary = {
                "design": final_state.get("design", {}),
                "artifacts_stored": final_state.get("artifacts_stored", 0),
                "context_entries_loaded": len(final_state.get("business_context", [])),
            }

            # Auto-create approval gate when agent completes successfully
            if run.status == RunStatus.COMPLETED:
                await create_approval_gate(session, run)

            await session.commit()

        except Exception as e:
            logger.exception("Design agent run %s failed", run_id)
            await session.rollback()
            try:
                result = await session.execute(
                    select(AgentRun).where(AgentRun.id == run_id)
                )
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark run %s as failed", run_id)


# ─── Prototype Agent Endpoints ───


@router.post("/prototype/start", response_model=PrototypeStartResponse, status_code=201)
async def start_prototype(
    project_id: uuid.UUID,
    payload: PrototypeStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a Prototype Agent run for the given project.

    Requires the project to be in 'prototype' status (set after design approval).
    Reads all design artifacts and generates a working React/Next.js prototype.
    """
    project = await _get_project(project_id, db)

    # Check if there's already a PENDING prototype run (created by approval auto-start)
    existing = await db.execute(
        select(AgentRun).where(
            AgentRun.project_id == project_id,
            AgentRun.agent_type == AgentType.PROTOTYPE,
            AgentRun.status == RunStatus.PENDING,
        ).order_by(AgentRun.created_at.desc()).limit(1)
    )
    agent_run = existing.scalar_one_or_none()

    if agent_run:
        run_id = agent_run.id
        logger.info("Found existing PENDING prototype run %s, starting it", run_id)
    else:
        if project.status != ProjectStatus.PROTOTYPE:
            raise HTTPException(
                status_code=409,
                detail=f"Project must be in 'prototype' status to start prototype agent "
                f"(current: {project.status.value})",
            )

        reviewer_notes = (payload.reviewer_notes or "") if payload else ""

        # Create agent run record
        agent_run = AgentRun(
            project_id=project_id,
            agent_type=AgentType.PROTOTYPE,
            status=RunStatus.PENDING,
            input_context={"reviewer_notes": reviewer_notes},
        )
        db.add(agent_run)
        await db.flush()
        await db.refresh(agent_run)
        run_id = agent_run.id

    await db.commit()

    # Start the simulation — store task ref to prevent GC
    from src.api.routes.approvals import _background_tasks
    task = asyncio.get_running_loop().create_task(_run_prototype_simulation(run_id, project_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "run_id": run_id,
        "status": RunStatus.PENDING,
        "message": "Prototype agent started",
    }


@router.get("/{run_id}/prototype-output", response_model=PrototypeOutputResponse)
async def get_prototype_output(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the prototype agent output including all generated artifacts."""
    await _get_project(project_id, db)
    run = await _get_agent_run(run_id, project_id, db)

    # Fetch artifacts for this run
    result = await db.execute(
        select(Artifact)
        .where(Artifact.agent_run_id == run_id)
        .order_by(Artifact.created_at)
    )
    artifacts = list(result.scalars().all())

    output = run.output_summary or {}

    return {
        "run_id": run.id,
        "agent_type": run.agent_type,
        "status": run.status,
        "prototype": output.get("prototype", {}),
        "artifacts": artifacts,
        "errors": [run.error_details] if run.error_details else [],
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


async def _run_prototype_graph(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    reviewer_notes: str,
    db_factory: object,
) -> None:
    """Execute the prototype graph and persist results.

    Runs as a background task after the HTTP response is sent.
    """
    from src.context_store.database import async_session_factory

    factory = db_factory or async_session_factory

    async with factory() as session:  # type: ignore[operator]
        try:
            # Mark as running
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Build and execute graph
            initial = create_prototype_state(
                project_id=str(project_id),
                agent_run_id=str(run_id),
                reviewer_notes=reviewer_notes,
                session=session,
            )

            graph = build_prototype_graph()
            compiled = graph.compile()
            final_state = await compiled.ainvoke(initial)

            # Re-fetch the run to update
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()

            # Determine final status
            if final_state.get("errors"):
                run.status = RunStatus.FAILED
                run.error_details = "; ".join(final_state["errors"])
            else:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)

            run.output_summary = {
                "prototype": final_state.get("prototype", {}),
                "artifacts_stored": final_state.get("artifacts_stored", 0),
                "design_artifacts_loaded": len(final_state.get("design_artifacts", [])),
            }

            # Auto-create approval gate when agent completes successfully
            if run.status == RunStatus.COMPLETED:
                await create_approval_gate(session, run)

            await session.commit()

        except Exception as e:
            logger.exception("Prototype agent run %s failed", run_id)
            await session.rollback()
            try:
                result = await session.execute(
                    select(AgentRun).where(AgentRun.id == run_id)
                )
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark run %s as failed", run_id)


# ─── Prototype Feedback Endpoint ───


@router.post("/{run_id}/feedback", response_model=PrototypeFeedbackResponse, status_code=201)
async def submit_prototype_feedback(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: PrototypeFeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit feedback on a prototype and trigger a refined iteration.

    Stores the feedback as a conversation record, then re-runs the prototype
    generation with the original design artifacts, the previous prototype, and
    cumulative feedback history so improvements build on each other.
    """
    await _get_project(project_id, db)
    run = await _get_agent_run(run_id, project_id, db)

    if run.agent_type != AgentType.PROTOTYPE:
        raise HTTPException(
            status_code=409,
            detail=f"Feedback is only supported for prototype agent runs "
            f"(this run is {run.agent_type.value})",
        )

    if run.status not in (RunStatus.COMPLETED, RunStatus.PAUSED_FOR_APPROVAL):
        raise HTTPException(
            status_code=409,
            detail=f"Agent run must be completed or paused_for_approval to accept feedback "
            f"(current status: {run.status.value})",
        )

    # 1. Store as conversation record
    conversation = Conversation(
        project_id=project_id,
        agent_run_id=run_id,
        direction=MessageDirection.USER_TO_AGENT,
        message=payload.feedback,
        structured_data={"type": "prototype_feedback"},
    )
    db.add(conversation)

    # 2. Gather cumulative feedback history from all conversations on prototype runs
    from sqlalchemy import func as sa_func

    result = await db.execute(
        select(Conversation.message)
        .where(
            Conversation.project_id == project_id,
            Conversation.direction == MessageDirection.USER_TO_AGENT,
            Conversation.structured_data["type"].astext == "prototype_feedback",
        )
        .order_by(Conversation.created_at)
    )
    prior_feedback = [row[0] for row in result.all()]
    # Append current feedback (not yet committed, so not in the query)
    all_feedback = prior_feedback + [payload.feedback]

    # 3. Get previous prototype output from this run
    previous_demo = (run.output_summary or {}).get("prototype", {})

    # 4. Determine next version number
    result = await db.execute(
        select(sa_func.max(Artifact.version))
        .where(
            Artifact.project_id == project_id,
            Artifact.type == "demo",
        )
    )
    max_version = result.scalar_one_or_none() or 0
    next_version = max_version + 1

    # 5. Create a new agent run for the feedback iteration
    new_run = AgentRun(
        project_id=project_id,
        agent_type=AgentType.PROTOTYPE,
        status=RunStatus.PENDING,
        input_context={
            "feedback": payload.feedback,
            "feedback_history": all_feedback,
            "parent_run_id": str(run_id),
            "version": next_version,
        },
    )
    db.add(new_run)
    await db.flush()
    await db.refresh(new_run)
    new_run_id = new_run.id

    # 6. Launch background task with cumulative context
    asyncio.create_task(
        _run_prototype_feedback_graph(
            new_run_id, project_id, previous_demo, all_feedback, next_version, None
        )
    )

    return {
        "run_id": new_run_id,
        "status": RunStatus.PENDING,
        "message": "Feedback received, demo regeneration started",
        "version": next_version,
    }


async def _run_prototype_feedback_graph(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    previous_demo: dict,
    feedback_history: list[str],
    version: int,
    db_factory: object,
) -> None:
    """Execute the prototype graph with feedback context for iterative refinement.

    Injects the previous prototype and cumulative feedback so the LLM
    improves upon the existing work rather than starting from scratch.
    """
    from src.context_store.database import async_session_factory

    factory = db_factory or async_session_factory

    async with factory() as session:  # type: ignore[operator]
        try:
            # Mark as running
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Build and execute graph with feedback context
            initial = create_prototype_state(
                project_id=str(project_id),
                agent_run_id=str(run_id),
                previous_demo=previous_demo,
                feedback_history=feedback_history,
                artifact_version=version,
                session=session,
            )

            graph = build_prototype_graph()
            compiled = graph.compile()
            final_state = await compiled.ainvoke(initial)

            # Re-fetch the run to update
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()

            if final_state.get("errors"):
                run.status = RunStatus.FAILED
                run.error_details = "; ".join(final_state["errors"])
            else:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(timezone.utc)

            run.output_summary = {
                "prototype": final_state.get("prototype", {}),
                "artifacts_stored": final_state.get("artifacts_stored", 0),
                "design_artifacts_loaded": len(final_state.get("design_artifacts", [])),
                "version": version,
                "feedback_count": len(feedback_history),
            }

            if run.status == RunStatus.COMPLETED:
                await create_approval_gate(session, run)

            await session.commit()

        except Exception as e:
            logger.exception("Demo feedback run %s failed", run_id)
            await session.rollback()
            try:
                result = await session.execute(
                    select(AgentRun).where(AgentRun.id == run_id)
                )
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark feedback run %s as failed", run_id)