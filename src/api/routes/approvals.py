"""Approval gate API routes."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.project import (
    ApprovalDecideResponse,
    ApprovalDecision,
    ApprovalGateDetailResponse,
    ApprovalGateResponse,
    ApprovalListResponse,
)
from src.context_store.database import get_db
from src.context_store.models import (
    AgentRun,
    AgentType,
    ApprovalGate,
    ApprovalStatus,
    Project,
    ProjectStatus,
    RunStatus,
)
from src.orchestrator.approval import PHASE_TRANSITIONS, process_decision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/approvals", tags=["approvals"])

# Keep references to background tasks so they don't get garbage-collected
_background_tasks: set[asyncio.Task] = set()


async def _safe_run_agent(
    fn, run_id: uuid.UUID, project_id: uuid.UUID, name: str
) -> None:
    """Run an agent in the background with error handling."""
    try:
        logger.info("Auto-starting %s agent (run %s)", name, run_id)
        await fn(run_id, project_id)
        logger.info("Agent %s (run %s) completed successfully", name, run_id)
    except Exception as exc:
        logger.exception("Agent %s (run %s) CRASHED: %s", name, run_id, exc)


# ─── Helpers ───


async def _get_project(project_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_gate(
    gate_id: uuid.UUID, project_id: uuid.UUID, db: AsyncSession
) -> ApprovalGate:
    result = await db.execute(
        select(ApprovalGate).where(
            ApprovalGate.id == gate_id,
            ApprovalGate.project_id == project_id,
        )
    )
    gate = result.scalar_one_or_none()
    if not gate:
        raise HTTPException(status_code=404, detail="Approval gate not found")
    return gate


# ─── Endpoints ───


@router.get("/", response_model=ApprovalListResponse)
async def list_approvals(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all approval gates for a project."""
    await _get_project(project_id, db)

    count_result = await db.execute(
        select(func.count(ApprovalGate.id)).where(
            ApprovalGate.project_id == project_id
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(ApprovalGate)
        .where(ApprovalGate.project_id == project_id)
        .order_by(ApprovalGate.created_at.desc())
    )
    gates = list(result.scalars().all())

    return {"approvals": gates, "total": total}


@router.get("/{gate_id}", response_model=ApprovalGateDetailResponse)
async def get_approval(
    project_id: uuid.UUID,
    gate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single approval gate with the agent's output summary."""
    await _get_project(project_id, db)
    gate = await _get_gate(gate_id, project_id, db)

    # Fetch the associated agent run for output details
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == gate.agent_run_id)
    )
    agent_run = result.scalar_one()

    return {
        "id": gate.id,
        "project_id": gate.project_id,
        "agent_run_id": gate.agent_run_id,
        "status": gate.status,
        "reviewer_notes": gate.reviewer_notes,
        "decided_at": gate.decided_at,
        "created_at": gate.created_at,
        "agent_type": agent_run.agent_type,
        "run_status": agent_run.status,
        "output_summary": agent_run.output_summary or {},
    }


@router.post("/{gate_id}/decide", response_model=ApprovalDecideResponse)
async def decide_approval(
    project_id: uuid.UUID,
    gate_id: uuid.UUID,
    payload: ApprovalDecision,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a decision on an approval gate.

    - approved: advances project to the next SDLC phase
    - rejected: marks the agent run as failed
    - revision_requested: marks agent run as failed for re-trigger with notes
    """
    project = await _get_project(project_id, db)
    gate = await _get_gate(gate_id, project_id, db)

    if gate.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Approval gate already decided (status: {gate.status.value})",
        )

    if payload.status == ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=422,
            detail="Cannot set status to 'pending'. Must be approved, rejected, or revision_requested.",
        )

    await process_decision(
        session=db,
        gate=gate,
        decision=payload.status,
        reviewer_notes=payload.reviewer_notes,
    )

    # If approved, auto-start the next agent
    next_run_id = None
    if payload.status == ApprovalStatus.APPROVED:
        result = await db.execute(select(AgentRun).where(AgentRun.id == gate.agent_run_id))
        completed_run = result.scalar_one()

        NEXT_AGENT: dict[str, tuple[str, object]] = {
            "ingest": ("discover", AgentType.DISCOVER),
            "discover": ("design", AgentType.DESIGN),
            "design": ("prototype", AgentType.PROTOTYPE),
            "prototype": ("plan", AgentType.PLAN),
            "plan": ("build", AgentType.BUILD),
            "build": ("test", AgentType.TEST),
            "test": ("ship", AgentType.SHIP),
        }

        current_agent = completed_run.agent_type.value
        if current_agent in NEXT_AGENT:
            next_name, next_type = NEXT_AGENT[current_agent]
            new_run = AgentRun(
                project_id=project_id,
                agent_type=next_type,  # type: ignore[arg-type]
                status=RunStatus.PENDING,
            )
            db.add(new_run)
            await db.flush()
            await db.refresh(new_run)
            next_run_id = str(new_run.id)
            logger.info(
                "Created PENDING %s run %s — frontend will call /start to begin it",
                next_name, next_run_id,
            )

    # If revision_requested, re-trigger the discovery agent with reviewer notes
    if payload.status == ApprovalStatus.REVISION_REQUESTED:
        # Fetch the original agent run to get its input context
        result = await db.execute(
            select(AgentRun).where(AgentRun.id == gate.agent_run_id)
        )
        original_run = result.scalar_one()

        reviewer_notes = payload.reviewer_notes or ""

        if original_run.agent_type == AgentType.DISCOVER:
            original_text = (original_run.input_context or {}).get("document_text", "")

            # Create a new agent run for the re-trigger
            new_run = AgentRun(
                project_id=project_id,
                agent_type=AgentType.DISCOVER,
                status=RunStatus.PENDING,
                input_context={
                    "document_text": original_text,
                    "reviewer_notes": reviewer_notes,
                },
            )
            db.add(new_run)
            await db.flush()
            await db.refresh(new_run)

            from src.api.routes.agents import _run_discovery_graph_with_responses

            # Inject reviewer notes as user responses for the re-run
            user_responses = [{"question": "Reviewer feedback", "answer": reviewer_notes}]
            asyncio.create_task(
                _run_discovery_graph_with_responses(
                    new_run.id, project_id, original_text, user_responses, None
                )
            )

        elif original_run.agent_type == AgentType.DESIGN:
            # Re-trigger design agent with reviewer notes
            new_run = AgentRun(
                project_id=project_id,
                agent_type=AgentType.DESIGN,
                status=RunStatus.PENDING,
                input_context={"reviewer_notes": reviewer_notes},
            )
            db.add(new_run)
            await db.flush()
            await db.refresh(new_run)

            from src.api.routes.agents import _run_design_graph

            asyncio.create_task(
                _run_design_graph(new_run.id, project_id, reviewer_notes, None)
            )

        elif original_run.agent_type == AgentType.PROTOTYPE:
            # Re-trigger demo agent with reviewer notes
            new_run = AgentRun(
                project_id=project_id,
                agent_type=AgentType.PROTOTYPE,
                status=RunStatus.PENDING,
                input_context={"reviewer_notes": reviewer_notes},
            )
            db.add(new_run)
            await db.flush()
            await db.refresh(new_run)

            from src.api.routes.agents import _run_prototype_graph

            asyncio.create_task(
                _run_prototype_graph(new_run.id, project_id, reviewer_notes, None)
            )

        elif original_run.agent_type == AgentType.PLAN:
            # Re-trigger define agent with reviewer notes
            new_run = AgentRun(
                project_id=project_id,
                agent_type=AgentType.PLAN,
                status=RunStatus.PENDING,
                input_context={"reviewer_notes": reviewer_notes},
            )
            db.add(new_run)
            await db.flush()
            await db.refresh(new_run)

            from src.api.routes.plan import _run_plan_graph

            asyncio.create_task(
                _run_plan_graph(new_run.id, project_id, reviewer_notes, None)
            )

    # Re-fetch project to get updated status
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one()

    # Build message
    if payload.status == ApprovalStatus.APPROVED:
        message = f"Approved. Project advanced to {project.status.value}."
    elif payload.status == ApprovalStatus.REJECTED:
        message = "Rejected. Agent run marked as failed."
    else:
        agent_label = original_run.agent_type.value.title()  # type: ignore[possibly-undefined]
        message = f"Revision requested. {agent_label} agent re-triggered with notes."

    resp: dict = {
        "id": gate.id,
        "status": gate.status,
        "project_status": project.status,
        "message": message,
    }
    if next_run_id:
        resp["next_run_id"] = next_run_id
    return resp