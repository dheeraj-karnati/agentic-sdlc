"""Plan agent CRUD routes for epics and user stories."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.plan.agent import (
    build_plan_graph,
    create_initial_state as create_plan_state,
    import_plan_to_db,
)
from src.api.schemas.project import (
    PlanOutputResponse,
    PlanStartRequest,
    PlanStartResponse,
    EpicResponse,
    EpicUpdate,
    PlanArtifactResponse,
    PlanImportResponse,
    ResequenceRequest,
    UserStoryCreate,
    UserStoryResponse,
    UserStoryUpdate,
)
from src.context_store.database import get_db
from src.context_store.models import (
    AgentRun,
    AgentType,
    Artifact,
    Epic,
    Project,
    ProjectStatus,
    RunStatus,
    UserStory,
)
from src.orchestrator.approval import create_approval_gate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/plan", tags=["plan"])


# ─── Helpers ───


async def _get_project(project_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_epic(
    epic_id: uuid.UUID, project_id: uuid.UUID, db: AsyncSession
) -> Epic:
    result = await db.execute(
        select(Epic).where(Epic.id == epic_id, Epic.project_id == project_id)
    )
    epic = result.scalar_one_or_none()
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")
    return epic


async def _get_story(
    story_id: uuid.UUID, project_id: uuid.UUID, db: AsyncSession
) -> UserStory:
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == story_id, UserStory.project_id == project_id
        )
    )
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="User story not found")
    return story


# ─── Start Plan Agent ───


@router.post("/start", response_model=PlanStartResponse, status_code=201)
async def start_plan(
    project_id: uuid.UUID,
    payload: PlanStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a Plan Agent run for the given project.

    Requires the project to be in 'plan' status (set after demo approval).
    """
    project = await _get_project(project_id, db)

    if project.status != ProjectStatus.PLAN:
        raise HTTPException(
            status_code=409,
            detail=f"Project must be in 'plan' status to start plan agent "
            f"(current: {project.status.value})",
        )

    reviewer_notes = (payload.reviewer_notes or "") if payload else ""

    agent_run = AgentRun(
        project_id=project_id,
        agent_type=AgentType.PLAN,
        status=RunStatus.PENDING,
        input_context={"reviewer_notes": reviewer_notes},
    )
    db.add(agent_run)
    await db.flush()
    await db.refresh(agent_run)
    run_id = agent_run.id

    asyncio.create_task(
        _run_plan_graph(run_id, project_id, reviewer_notes, None)
    )

    return {
        "run_id": run_id,
        "status": RunStatus.PENDING,
        "message": "Plan agent started",
    }


@router.get("/{run_id}/output", response_model=PlanOutputResponse)
async def get_plan_output(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the plan agent output including epics and stories."""
    await _get_project(project_id, db)

    result = await db.execute(
        select(AgentRun).where(
            AgentRun.id == run_id, AgentRun.project_id == project_id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    # Fetch epics and stories
    result = await db.execute(
        select(Epic)
        .where(Epic.project_id == project_id, Epic.agent_run_id == run_id)
        .order_by(Epic.sequence_order)
    )
    epics = list(result.scalars().all())

    result = await db.execute(
        select(UserStory)
        .where(UserStory.project_id == project_id)
        .order_by(UserStory.sequence_order)
    )
    stories = list(result.scalars().all())

    return {
        "run_id": run.id,
        "agent_type": run.agent_type,
        "status": run.status,
        "epics": epics,
        "stories": stories,
        "errors": [run.error_details] if run.error_details else [],
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


# ─── Plan Artifact & Import ───


@router.get("/{run_id}/artifact", response_model=PlanArtifactResponse)
async def get_plan_artifact(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the plan artifact JSON for review before import."""
    await _get_project(project_id, db)

    result = await db.execute(
        select(Artifact).where(
            Artifact.project_id == project_id,
            Artifact.agent_run_id == run_id,
            Artifact.type == "plan",
        )
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Plan artifact not found")

    try:
        plan_data = json.loads(artifact.content) if artifact.content else {}
    except json.JSONDecodeError:
        plan_data = {}

    return {
        "artifact_id": artifact.id,
        "run_id": run_id,
        "plan": plan_data,
        "version": artifact.version,
        "created_at": artifact.created_at,
    }


@router.post("/{run_id}/import", response_model=PlanImportResponse)
async def import_plan(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Import the plan artifact into epics and user_stories tables.

    Call this after reviewing and approving the plan artifact.
    """
    await _get_project(project_id, db)

    # Fetch the plan artifact
    result = await db.execute(
        select(Artifact).where(
            Artifact.project_id == project_id,
            Artifact.agent_run_id == run_id,
            Artifact.type == "plan",
        )
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Plan artifact not found")

    try:
        plan_data = json.loads(artifact.content) if artifact.content else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid plan artifact JSON")

    if not plan_data.get("epics"):
        raise HTTPException(status_code=422, detail="Plan artifact has no epics")

    # Check if already imported (epics exist for this run)
    result = await db.execute(
        select(Epic).where(
            Epic.project_id == project_id, Epic.agent_run_id == run_id
        )
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=409, detail="Plan has already been imported for this run"
        )

    counts = await import_plan_to_db(db, project_id, run_id, plan_data)

    return {
        "run_id": run_id,
        "epics_imported": counts["epics_stored"],
        "stories_imported": counts["stories_stored"],
        "message": f"Imported {counts['epics_stored']} epics and {counts['stories_stored']} stories",
    }


# ─── Epic CRUD ───


@router.get("/epics", response_model=list[EpicResponse])
async def list_epics(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list:
    """List all epics for a project, ordered by sequence."""
    await _get_project(project_id, db)
    result = await db.execute(
        select(Epic)
        .where(Epic.project_id == project_id)
        .order_by(Epic.sequence_order)
    )
    return list(result.scalars().all())


@router.put("/epics/{epic_id}", response_model=EpicResponse)
async def update_epic(
    project_id: uuid.UUID,
    epic_id: uuid.UUID,
    payload: EpicUpdate,
    db: AsyncSession = Depends(get_db),
) -> Epic:
    """Update an epic's fields."""
    await _get_project(project_id, db)
    epic = await _get_epic(epic_id, project_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(epic, field, value)

    await db.flush()
    await db.refresh(epic)
    return epic


# ─── User Story CRUD ───


@router.get("/stories", response_model=list[UserStoryResponse])
async def list_stories(
    project_id: uuid.UUID,
    epic_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list:
    """List user stories, optionally filtered by epic."""
    await _get_project(project_id, db)
    query = select(UserStory).where(UserStory.project_id == project_id)
    if epic_id:
        query = query.where(UserStory.epic_id == epic_id)
    query = query.order_by(UserStory.sequence_order)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/stories", response_model=UserStoryResponse, status_code=201)
async def create_story(
    project_id: uuid.UUID,
    payload: UserStoryCreate,
    db: AsyncSession = Depends(get_db),
) -> UserStory:
    """Create a new user story. Agent auto-generates technical fields via LLM if empty."""
    await _get_project(project_id, db)
    await _get_epic(payload.epic_id, project_id, db)

    # Determine next sequence_order
    from sqlalchemy import func as sa_func

    result = await db.execute(
        select(sa_func.max(UserStory.sequence_order))
        .where(UserStory.epic_id == payload.epic_id)
    )
    max_seq = result.scalar_one_or_none() or 0

    story = UserStory(
        epic_id=payload.epic_id,
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        acceptance_criteria=payload.acceptance_criteria,
        story_points=payload.story_points,
        priority=payload.priority,
        sequence_order=max_seq + 1,
    )
    db.add(story)
    await db.flush()
    await db.refresh(story)
    return story


@router.put("/stories/{story_id}", response_model=UserStoryResponse)
async def update_story(
    project_id: uuid.UUID,
    story_id: uuid.UUID,
    payload: UserStoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserStory:
    """Update a user story's fields."""
    await _get_project(project_id, db)
    story = await _get_story(story_id, project_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)

    await db.flush()
    await db.refresh(story)
    return story


@router.delete("/stories/{story_id}", status_code=204)
async def delete_story(
    project_id: uuid.UUID,
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a user story. Removes dependency references from other stories."""
    await _get_project(project_id, db)
    story = await _get_story(story_id, project_id, db)

    story_title = story.title

    # Remove dependency references from other stories
    result = await db.execute(
        select(UserStory).where(UserStory.project_id == project_id)
    )
    for other in result.scalars().all():
        deps = other.dependencies or []
        if story_title in deps:
            other.dependencies = [d for d in deps if d != story_title]

    await db.delete(story)
    await db.flush()


@router.post("/stories/resequence", status_code=200)
async def resequence_stories(
    project_id: uuid.UUID,
    payload: ResequenceRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reorder stories by setting new sequence_order values."""
    await _get_project(project_id, db)

    for item in payload.stories:
        result = await db.execute(
            select(UserStory).where(
                UserStory.id == item.id, UserStory.project_id == project_id
            )
        )
        story = result.scalar_one_or_none()
        if not story:
            raise HTTPException(
                status_code=404, detail=f"Story {item.id} not found"
            )
        story.sequence_order = item.sequence_order

    await db.flush()
    return {"message": f"Resequenced {len(payload.stories)} stories"}


# ─── Background Task ───


async def _run_plan_graph(
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    reviewer_notes: str,
    db_factory: object,
) -> None:
    """Execute the plan graph and persist results.

    Uses phased session management: separate DB sessions for context gathering,
    LLM work (no session), and artifact storage. This prevents connection
    timeouts during slow LLM inference.
    """
    from src.agents.plan.agent import (
        gather_context,
        generate_plan,
        store_artifact,
        validate_plan,
    )
    from src.context_store.database import async_session_factory

    factory = db_factory or async_session_factory

    try:
        # Phase 1: Mark as running
        async with factory() as session:  # type: ignore[operator]
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == run_id)
            )
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

        # Phase 2: Gather context (DB read -- short session)
        async with factory() as session:  # type: ignore[operator]
            state = create_plan_state(
                project_id=str(project_id),
                agent_run_id=str(run_id),
                reviewer_notes=reviewer_notes,
                session=session,
            )
            ctx_result = await gather_context(state)
            state.update(ctx_result)

        # Phase 3: LLM call (no DB session needed)
        state["_session"] = None
        plan_result = await generate_plan(state)
        state.update(plan_result)

        val_result = await validate_plan(state)
        state.update(val_result)

        # Phase 4: Store artifact (fresh DB session)
        async with factory() as session:  # type: ignore[operator]
            state["_session"] = session
            artifact_result = await store_artifact(state)
            state.update(artifact_result)
            await session.commit()

        final_state = state

        # Phase 5: Update run status
        async with factory() as session:  # type: ignore[operator]
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

            plan = final_state.get("plan", {})
            epics = plan.get("epics", [])
            total_stories = sum(len(e.get("stories", [])) for e in epics)
            run.output_summary = {
                "epics_count": len(epics),
                "stories_count": total_stories,
                "plan_artifact_id": final_state.get("plan_artifact_id"),
                "validation_issues": final_state.get("validation_issues", []),
            }

            if run.status == RunStatus.COMPLETED:
                await create_approval_gate(session, run)

            await session.commit()

    except Exception as e:
        logger.exception("Plan agent run %s failed", run_id)
        try:
            async with factory() as session:  # type: ignore[operator]
                result = await session.execute(
                    select(AgentRun).where(AgentRun.id == run_id)
                )
                run = result.scalar_one()
                run.status = RunStatus.FAILED
                run.error_details = str(e)
                await session.commit()
        except Exception:
            logger.exception("Failed to mark plan run %s as failed", run_id)
