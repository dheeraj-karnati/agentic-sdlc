"""Unit tests for src/orchestrator/approval.py."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.context_store.models import (
    AgentRun,
    AgentType,
    ApprovalGate,
    ApprovalStatus,
    Project,
    ProjectStatus,
    RunStatus,
)
from src.orchestrator.approval import (
    PHASE_TRANSITIONS,
    create_approval_gate,
    process_decision,
)


# ─── Factories ───

PROJECT_ID = uuid.uuid4()
RUN_ID = uuid.uuid4()
GATE_ID = uuid.uuid4()


def _make_agent_run(
    agent_type: AgentType = AgentType.DISCOVER,
    status: RunStatus = RunStatus.COMPLETED,
) -> AgentRun:
    run = AgentRun(
        id=RUN_ID,
        project_id=PROJECT_ID,
        agent_type=agent_type,
        status=status,
    )
    return run


def _make_gate(status: ApprovalStatus = ApprovalStatus.PENDING) -> ApprovalGate:
    gate = ApprovalGate(
        id=GATE_ID,
        project_id=PROJECT_ID,
        agent_run_id=RUN_ID,
        status=status,
    )
    gate.created_at = datetime.now(timezone.utc)
    return gate


def _make_project(status: ProjectStatus = ProjectStatus.DISCOVER) -> Project:
    p = Project(id=PROJECT_ID, name="Test", status=status)
    return p


def _mock_session(agent_run: AgentRun, project: Project) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        # process_decision fetches agent_run first, then project
        if call_count == 1:
            result.scalar_one.return_value = agent_run
        else:
            result.scalar_one.return_value = project
        return result

    session.execute = AsyncMock(side_effect=fake_execute)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ─── create_approval_gate tests ───


@pytest.mark.asyncio
async def test_create_approval_gate_sets_pending() -> None:
    """Creates a gate with pending status and pauses the agent run."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    run = _make_agent_run(status=RunStatus.COMPLETED)
    gate = await create_approval_gate(session, run)

    assert run.status == RunStatus.PAUSED_FOR_APPROVAL
    session.add.assert_called_once()
    added = session.add.call_args[0][0]
    assert isinstance(added, ApprovalGate)
    assert added.project_id == PROJECT_ID
    assert added.agent_run_id == RUN_ID
    assert added.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_create_approval_gate_flushes() -> None:
    """Gate creation flushes and refreshes the session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    run = _make_agent_run()
    await create_approval_gate(session, run)

    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once()


# ─── process_decision: approved ───


@pytest.mark.asyncio
async def test_approve_advances_project() -> None:
    """Approving discovery advances project to design phase."""
    run = _make_agent_run(agent_type=AgentType.DISCOVER)
    project = _make_project(status=ProjectStatus.DISCOVER)
    session = _mock_session(run, project)
    gate = _make_gate()

    await process_decision(session, gate, ApprovalStatus.APPROVED, "Looks good")

    assert gate.status == ApprovalStatus.APPROVED
    assert gate.reviewer_notes == "Looks good"
    assert gate.decided_at is not None
    assert run.status == RunStatus.COMPLETED
    assert run.completed_at is not None
    assert project.status == ProjectStatus.DESIGN


@pytest.mark.asyncio
async def test_approve_design_advances_to_demo() -> None:
    """Approving design phase advances to demo."""
    run = _make_agent_run(agent_type=AgentType.DESIGN)
    project = _make_project(status=ProjectStatus.DESIGN)
    session = _mock_session(run, project)
    gate = _make_gate()

    await process_decision(session, gate, ApprovalStatus.APPROVED)

    assert project.status == ProjectStatus.PROTOTYPE


@pytest.mark.asyncio
async def test_approve_deployment_completes_project() -> None:
    """Approving deployment marks project as completed."""
    run = _make_agent_run(agent_type=AgentType.SHIP)
    project = _make_project(status=ProjectStatus.SHIP)
    session = _mock_session(run, project)
    gate = _make_gate()

    await process_decision(session, gate, ApprovalStatus.APPROVED)

    assert project.status == ProjectStatus.COMPLETED


# ─── process_decision: rejected ───


@pytest.mark.asyncio
async def test_reject_fails_agent_run() -> None:
    """Rejecting marks the agent run as failed."""
    run = _make_agent_run()
    project = _make_project()
    session = _mock_session(run, project)
    gate = _make_gate()

    await process_decision(session, gate, ApprovalStatus.REJECTED, "Not ready")

    assert gate.status == ApprovalStatus.REJECTED
    assert run.status == RunStatus.FAILED
    assert "Rejected" in (run.error_details or "")
    assert "Not ready" in (run.error_details or "")


@pytest.mark.asyncio
async def test_reject_does_not_advance_project() -> None:
    """Rejecting does not change project status."""
    run = _make_agent_run()
    project = _make_project(status=ProjectStatus.DISCOVER)
    session = _mock_session(run, project)
    gate = _make_gate()

    await process_decision(session, gate, ApprovalStatus.REJECTED)

    assert project.status == ProjectStatus.DISCOVER


# ─── process_decision: revision_requested ───


@pytest.mark.asyncio
async def test_revision_requested_fails_run() -> None:
    """Requesting revision marks run as failed for re-trigger."""
    run = _make_agent_run()
    project = _make_project()
    session = _mock_session(run, project)
    gate = _make_gate()

    await process_decision(
        session, gate, ApprovalStatus.REVISION_REQUESTED, "Need more detail on auth"
    )

    assert gate.status == ApprovalStatus.REVISION_REQUESTED
    assert run.status == RunStatus.FAILED
    assert "Revision requested" in (run.error_details or "")
    assert "Need more detail on auth" in (run.error_details or "")


@pytest.mark.asyncio
async def test_revision_does_not_advance_project() -> None:
    """Revision request does not change project status."""
    run = _make_agent_run()
    project = _make_project(status=ProjectStatus.DISCOVER)
    session = _mock_session(run, project)
    gate = _make_gate()

    await process_decision(session, gate, ApprovalStatus.REVISION_REQUESTED)

    assert project.status == ProjectStatus.DISCOVER


# ─── PHASE_TRANSITIONS coverage ───


def test_all_agent_types_have_transitions() -> None:
    """Every agent type maps to a next project status."""
    for agent_type in AgentType:
        assert agent_type in PHASE_TRANSITIONS