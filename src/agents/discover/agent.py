"""Discovery Agent: Workflow -> Task -> Skill architecture.

Analyzes legacy application artifacts (code, documents, schemas) to produce
a comprehensive system understanding for the Design Agent.

Graph structure:
    parse_and_classify → deep_analysis → generate_understanding →
    generate_questions → quality_assessment → [conditional]
        ├─ pass → clarification_check → [conditional]
        │                                   ├─ has_questions → END (interrupt)
        │                                   └─ clear → store_and_complete → END
        ├─ retry → deep_analysis (max 2 retries)
        └─ max_retries_reached → clarification_check → ...
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.agents.base.workflow import BaseWorkflow
from src.agents.discover.tasks.deep_analysis_task import (
    DeepAnalysisInput,
    DeepAnalysisTask,
)
from src.agents.discover.tasks.generate_clarification_questions_task import (
    ClarificationQuestionsInput,
    GenerateClarificationQuestionsTask,
)
from src.agents.discover.tasks.generate_system_understanding_task import (
    GenerateSystemUnderstandingTask,
    SystemUnderstandingInput,
)
from src.agents.discover.tasks.parse_and_classify_task import (
    ClassifiedInputs,
    InputFile,
    ParseAndClassifyInput,
    ParseAndClassifyTask,
)
from src.agents.discover.tasks.quality_assessment_task import (
    QualityAssessmentInput,
    QualityAssessmentTask,
)
from src.context_store.models import AgentType
from src.context_store.repository import BusinessContextRepository
from src.tools.embeddings import embed_text
from src.tools.llm import get_llm

logger = logging.getLogger(__name__)


# ─── Agent State ───


class DiscoverState(TypedDict, total=False):
    """State for the Discovery Agent workflow."""

    # Input
    project_id: str
    document_text: str
    files: list[dict[str, str]]  # [{"filename": ..., "content": ...}]

    # Task outputs (stored as dicts for serialization)
    task_outputs: dict[str, Any]

    # Clarification / HITL
    pending_questions: list[dict[str, Any]]
    user_responses: list[dict[str, Any]]

    # Quality gate
    quality_score: float
    quality_suggestions: list[str]
    quality_retries: int

    # Store output
    stored_count: int

    # Control
    skip_clarity: bool
    errors: list[str]
    updated_at: str

    # Dependencies (injected, not serialized)
    _llm: BaseChatModel | None
    _repository: BusinessContextRepository | None
    _embed_fn: object | None


def create_initial_state(
    project_id: str,
    document_text: str = "",
    files: list[dict[str, str]] | None = None,
    llm: BaseChatModel | None = None,
    repository: BusinessContextRepository | None = None,
    embed_fn: object | None = None,
) -> DiscoverState:
    """Create a fresh state for the Discovery Agent."""
    return DiscoverState(
        project_id=project_id,
        document_text=document_text,
        files=files or [],
        task_outputs={},
        pending_questions=[],
        user_responses=[],
        quality_score=0.0,
        quality_suggestions=[],
        quality_retries=0,
        stored_count=0,
        skip_clarity=False,
        errors=[],
        updated_at=datetime.now(timezone.utc).isoformat(),
        _llm=llm,
        _repository=repository,
        _embed_fn=embed_fn,
    )


# ─── Helper ───


def _get_llm(state: DiscoverState) -> BaseChatModel:
    if state.get("_llm") is not None:
        return state["_llm"]  # type: ignore[return-value]
    return get_llm(max_tokens=8192)


# ─── Node Functions ───


async def load_ingested_sources(state: DiscoverState) -> dict[str, Any]:
    """Load pre-digitized sources from business_context (output of Digitize Agent).

    If digitized sources exist, converts them to ClassifiedInputs format so
    Discovery can work identically regardless of whether Digitize ran or raw
    files were provided directly.
    """
    repo = state.get("_repository")
    if repo is None:
        return {"updated_at": datetime.now(timezone.utc).isoformat()}

    try:
        project_uuid = uuid.UUID(state["project_id"])
        # Query for Digitize Agent outputs
        from sqlalchemy import select
        from src.context_store.models import BusinessContext
        entries = []
        # Use the repository's session to query digitized sources
        stmt = select(BusinessContext).where(
            BusinessContext.project_id == project_uuid,
            BusinessContext.category == "ingested_source",
        )
        result = await repo.session.execute(stmt)
        entries = list(result.scalars().all())

        if not entries:
            logger.info("No digitized sources found — Discovery will use direct file input")
            return {"updated_at": datetime.now(timezone.utc).isoformat()}

        # Convert digitized sources to ClassifiedInputs format
        items = []
        has_code = False
        for entry in entries:
            meta = entry.metadata_ or {}
            content_type = meta.get("content_type", "brd")
            input_type = meta.get("input_type", "document")
            if content_type == "source_code" or input_type == "code":
                has_code = True
            items.append({
                "source": entry.title or "ingested_source",
                "content_type": content_type,
                "language": "python" if content_type == "source_code" else "",
                "content": entry.content,
            })

        task_outputs = dict(state.get("task_outputs", {}))
        task_outputs["parse_and_classify"] = {
            "items": items,
            "classification_reasoning": f"Loaded {len(items)} digitized sources from Digitize Agent",
        }
        # Track whether this is a greenfield project (no source code)
        task_outputs["is_greenfield"] = not has_code

        logger.info("Loaded %d digitized sources (greenfield=%s)", len(items), not has_code)
        return {"task_outputs": task_outputs, "updated_at": datetime.now(timezone.utc).isoformat()}

    except Exception as e:
        logger.warning("load_ingested_sources failed (will fall back to direct input): %s", e)
        return {"updated_at": datetime.now(timezone.utc).isoformat()}


async def parse_and_classify(state: DiscoverState) -> dict[str, Any]:
    """Classify all inputs by content type."""
    llm = _get_llm(state)
    task = ParseAndClassifyTask()

    input_files = [
        InputFile(filename=f.get("filename", ""), content=f.get("content", ""))
        for f in state.get("files", [])
    ]
    raw_text = state.get("document_text", "")

    try:
        result = await task.execute(
            ParseAndClassifyInput(files=input_files, raw_text=raw_text),
            llm=llm,
        )
        task_outputs = dict(state.get("task_outputs", {}))
        task_outputs["parse_and_classify"] = result.model_dump(mode="json")
        return {
            "task_outputs": task_outputs,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        import traceback

        error_detail = f"{type(e).__name__}: {e}"
        logger.error("parse_and_classify failed: %s", error_detail, exc_info=True)
        print(f"parse_and_classify failed: {error_detail}", flush=True)
        traceback.print_exc()
        return {
            "errors": state.get("errors", []) + [f"parse_and_classify failed: {error_detail}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


async def deep_analysis(state: DiscoverState) -> dict[str, Any]:
    """Run all extraction skills across classified inputs."""
    llm = _get_llm(state)
    task = DeepAnalysisTask(llm=llm)

    task_outputs = state.get("task_outputs", {})
    classified_data = task_outputs.get("parse_and_classify", {})

    # If no classified data, create a fallback from raw text or files
    if not classified_data or not classified_data.get("items"):
        fallback_items = []
        # Use files if available
        for f in state.get("files", []):
            filename = f.get("filename", "unknown")
            content = f.get("content", "")
            # Infer type from file extension
            ct = "brd"
            if filename.endswith((".py", ".js", ".java", ".ts", ".go", ".rs")):
                ct = "source_code"
            elif filename.endswith(".sql"):
                ct = "schema"
            elif "meeting" in filename.lower() or "notes" in filename.lower():
                ct = "meeting_notes"
            lang = "python" if filename.endswith(".py") else ""
            fallback_items.append({
                "source": filename,
                "content_type": ct,
                "language": lang,
                "content": content,
            })
        # Fallback to raw text
        raw_text = state.get("document_text", "")
        if not fallback_items and raw_text:
            fallback_items.append({
                "source": "raw_input",
                "content_type": "brd",
                "language": "",
                "content": raw_text,
            })
        if fallback_items:
            classified_data = {
                "items": fallback_items,
                "classification_reasoning": "Fallback: inferred from file extensions",
            }

    improvement_ctx = ""
    suggestions = state.get("quality_suggestions", [])
    if suggestions:
        improvement_ctx = (
            "Previous quality assessment suggested improvements:\n"
            + "\n".join(f"- {s}" for s in suggestions)
        )

    try:
        classified = ClassifiedInputs.model_validate(classified_data)
        result = await task.execute(
            DeepAnalysisInput(
                classified_inputs=classified,
                improvement_context=improvement_ctx,
            ),
            llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["deep_analysis"] = result.model_dump(mode="json")
        return {
            "task_outputs": new_outputs,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        import traceback

        error_detail = f"{type(e).__name__}: {e}"
        logger.error("deep_analysis failed: %s", error_detail, exc_info=True)
        print(f"deep_analysis failed: {error_detail}", flush=True)
        traceback.print_exc()
        return {
            "errors": state.get("errors", []) + [f"deep_analysis failed: {error_detail}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


async def generate_understanding(state: DiscoverState) -> dict[str, Any]:
    """Synthesize all analysis into comprehensive system understanding."""
    llm = _get_llm(state)
    task = GenerateSystemUnderstandingTask()

    task_outputs = state.get("task_outputs", {})
    deep = task_outputs.get("deep_analysis", {})

    try:
        result = await task.execute(
            SystemUnderstandingInput(deep_analysis=deep),
            llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["system_understanding"] = result.model_dump(mode="json")
        return {
            "task_outputs": new_outputs,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("generate_understanding failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"generate_understanding failed: {e}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


async def generate_questions(state: DiscoverState) -> dict[str, Any]:
    """Generate clarification questions from conflicts and gaps."""
    llm = _get_llm(state)
    task = GenerateClarificationQuestionsTask()

    task_outputs = state.get("task_outputs", {})
    deep = task_outputs.get("deep_analysis", {})

    try:
        result = await task.execute(
            ClarificationQuestionsInput(
                conflict_report=deep.get("conflict_report", {}),
                entities=deep.get("entities", []),
                business_rules=deep.get("business_rules", []),
            ),
            llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["clarification_questions"] = result.model_dump(mode="json")

        # Also set pending_questions for the HITL interrupt check
        questions = result.model_dump(mode="json").get("questions", [])
        return {
            "task_outputs": new_outputs,
            "pending_questions": questions,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("generate_questions failed: %s", e)
        return {
            "errors": state.get("errors", []) + [f"generate_questions failed: {e}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


async def quality_assessment(state: DiscoverState) -> dict[str, Any]:
    """Score the discovery output quality."""
    llm = _get_llm(state)
    task = QualityAssessmentTask()

    task_outputs = state.get("task_outputs", {})

    try:
        result = await task.execute(
            QualityAssessmentInput(
                deep_analysis=task_outputs.get("deep_analysis", {}),
                system_understanding=task_outputs.get("system_understanding", {}),
                clarification_questions=task_outputs.get("clarification_questions", {}),
            ),
            llm=llm,
        )
        new_outputs = dict(task_outputs)
        new_outputs["quality_assessment"] = result.model_dump(mode="json")
        return {
            "task_outputs": new_outputs,
            "quality_score": result.overall_score,
            "quality_suggestions": result.suggestions,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("quality_assessment failed: %s", e)
        # On failure, set a passing score to avoid blocking
        return {
            "quality_score": 75.0,
            "quality_suggestions": [],
            "errors": state.get("errors", []) + [f"quality_assessment failed: {e}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


async def increment_quality_retry(state: DiscoverState) -> dict[str, Any]:
    """Increment the quality retry counter before looping back."""
    return {
        "quality_retries": state.get("quality_retries", 0) + 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def store_and_complete(state: DiscoverState) -> dict[str, Any]:
    """Save all outputs to business_context with embeddings."""
    repo = state.get("_repository")
    efn = state.get("_embed_fn", embed_text)
    project_uuid = uuid.UUID(state["project_id"])
    stored = 0

    task_outputs = state.get("task_outputs", {})
    deep = task_outputs.get("deep_analysis", {})

    # Store business rules
    for rule in deep.get("business_rules", []):
        title = rule.get("rule_name", rule.get("rule_id", "Untitled Rule"))
        content = json.dumps(rule, indent=2)
        embedding = None
        try:
            if efn is not None:
                embedding = await efn(f"{title}: {rule.get('description', '')}")  # type: ignore[misc]
        except Exception:
            pass

        if repo is not None:
            try:
                await repo.store_context(
                    project_id=project_uuid,
                    category="business_rule",
                    title=title,
                    content=content,
                    embedding=embedding,
                    source_agent=AgentType.DISCOVER,
                    metadata=rule,
                )
                stored += 1
            except Exception as e:
                logger.error("Failed to store rule '%s': %s", title, e)

    # Store entities
    for entity in deep.get("entities", []):
        title = entity.get("entity_name", "Untitled Entity")
        content = json.dumps(entity, indent=2)
        embedding = None
        try:
            if efn is not None:
                embedding = await efn(f"{title}: {entity.get('description', '')}")  # type: ignore[misc]
        except Exception:
            pass

        if repo is not None:
            try:
                await repo.store_context(
                    project_id=project_uuid,
                    category="domain_entity",
                    title=title,
                    content=content,
                    embedding=embedding,
                    source_agent=AgentType.DISCOVER,
                    metadata=entity,
                )
                stored += 1
            except Exception as e:
                logger.error("Failed to store entity '%s': %s", title, e)

    # Store system understanding as a single context entry
    understanding = task_outputs.get("system_understanding", {})
    if understanding:
        content = json.dumps(understanding, indent=2)
        embedding = None
        try:
            if efn is not None:
                purpose = understanding.get("system_purpose", "")[:500]
                embedding = await efn(purpose)  # type: ignore[misc]
        except Exception:
            pass

        if repo is not None:
            try:
                await repo.store_context(
                    project_id=project_uuid,
                    category="system_understanding",
                    title="System Understanding",
                    content=content,
                    embedding=embedding,
                    source_agent=AgentType.DISCOVER,
                    metadata={"quality_score": state.get("quality_score", 0.0)},
                )
                stored += 1
            except Exception as e:
                logger.error("Failed to store system understanding: %s", e)

    return {
        "stored_count": stored,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Routing Functions ───


def quality_gate(state: DiscoverState) -> str:
    """Route based on quality score."""
    score = state.get("quality_score", 0.0)
    retries = state.get("quality_retries", 0)

    if score >= 70.0:
        return "pass"
    if retries >= 2:
        logger.warning(
            "Quality score %.1f below 70 after %d retries — proceeding anyway",
            score, retries,
        )
        return "max_retries_reached"
    return "retry"


def clarification_check(state: DiscoverState) -> str:
    """Route based on pending questions."""
    if state.get("skip_clarity", False):
        return "clear"
    questions = state.get("pending_questions", [])
    if questions:
        return "has_questions"
    return "clear"


# ─── Workflow ───


class DiscoverWorkflow(BaseWorkflow):
    """Discovery Agent workflow using the Task -> Skill architecture."""

    name = "discover"
    description = "Analyze legacy application artifacts to produce a comprehensive system understanding"
    quality_threshold = 70.0
    max_quality_retries = 2

    def build_graph(self) -> StateGraph:
        graph = StateGraph(DiscoverState)

        # Nodes
        graph.add_node("load_ingested_sources", load_ingested_sources)
        graph.add_node("parse_and_classify", parse_and_classify)
        graph.add_node("deep_analysis", deep_analysis)
        graph.add_node("generate_understanding", generate_understanding)
        graph.add_node("generate_questions", generate_questions)
        graph.add_node("quality_assessment", quality_assessment)
        graph.add_node("increment_quality_retry", increment_quality_retry)
        graph.add_node("store_and_complete", store_and_complete)

        # Edges: main pipeline
        # load_ingested_sources reads from Digitize Agent output if available,
        # then parse_and_classify handles any additional raw files or serves as fallback
        graph.set_entry_point("load_ingested_sources")
        graph.add_edge("load_ingested_sources", "parse_and_classify")
        graph.add_edge("parse_and_classify", "deep_analysis")
        graph.add_edge("deep_analysis", "generate_understanding")
        graph.add_edge("generate_understanding", "generate_questions")
        graph.add_edge("generate_questions", "quality_assessment")

        # Quality gate: pass / retry / max_retries_reached
        graph.add_conditional_edges(
            "quality_assessment",
            quality_gate,
            {
                "pass": "store_and_complete",
                "retry": "increment_quality_retry",
                "max_retries_reached": "store_and_complete",
            },
        )

        # Retry loop: increment counter then re-run deep analysis
        graph.add_edge("increment_quality_retry", "deep_analysis")

        # After storing, check for clarification questions
        # (questions were already generated; we just need to decide whether to interrupt)
        graph.add_conditional_edges(
            "store_and_complete",
            clarification_check,
            {
                "has_questions": END,  # Caller resumes after user answers
                "clear": END,
            },
        )

        return graph

    def create_initial_state(self, **kwargs: Any) -> dict[str, Any]:
        return create_initial_state(**kwargs)  # type: ignore[arg-type]


def build_discover_graph() -> StateGraph:
    """Convenience function for backward compatibility."""
    workflow = DiscoverWorkflow()
    return workflow.build_graph()
