"""Unit tests for approval API routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
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


# ─── Constants ───

PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
RUN_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
GATE_ID = uuid.UUID("00000000-0000-0000-0000-000000000088")


# ─── Factories ───


def _make_project(status: ProjectStatus = ProjectStatus.DISCOVER) -> MagicMock:
    p = MagicMock(spec=Project)
    p.id = PROJECT_ID
    p.name = "Test"
    p.status = status
    return p


def _make_agent_run(
    status: RunStatus = RunStatus.PAUSED_FOR_APPROVAL,
    output_summary: dict | None = None,
) -> MagicMock:
    run = MagicMock(spec=AgentRun)
    run.id = RUN_ID
    run.project_id = PROJECT_ID
    run.agent_type = AgentType.DISCOVER
    run.status = status
    run.output_summary = output_summary or {"findings": {"business_rules": []}}
    run.error_details = None
    run.started_at = datetime.now(timezone.utc)
    run.completed_at = None
    run.created_at = datetime.now(timezone.utc)
    return run


def _make_gate(status: ApprovalStatus = ApprovalStatus.PENDING) -> MagicMock:
    gate = MagicMock(spec=ApprovalGate)
    gate.id = GATE_ID
    gate.project_id = PROJECT_ID
    gate.agent_run_id = RUN_ID
    gate.status = status
    gate.reviewer_notes = None
    gate.decided_at = None
    gate.created_at = datetime.now(timezone.utc)
    return gate


def _mock_db_for_list(project: MagicMock, gates: list[MagicMock], total: int) -> AsyncMock:
    """DB mock for list_approvals: project lookup, count, select."""
    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        elif call_count == 2:
            result.scalar_one.return_value = total
        else:
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = gates
            result.scalars.return_value = scalars_mock
        return result

    db.execute = AsyncMock(side_effect=fake_execute)
    return db


def _mock_db_for_detail(
    project: MagicMock, gate: MagicMock | None, agent_run: MagicMock | None = None
) -> AsyncMock:
    """DB mock for get_approval: project, gate, agent_run."""
    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        elif call_count == 2:
            result.scalar_one_or_none.return_value = gate
        else:
            result.scalar_one.return_value = agent_run
        return result

    db.execute = AsyncMock(side_effect=fake_execute)
    return db


def _mock_db_for_decide(
    project: MagicMock,
    gate: MagicMock | None,
    agent_run: MagicMock | None = None,
    project_after: MagicMock | None = None,
) -> AsyncMock:
    """DB mock for decide: project, gate, then process_decision internals, then re-fetch project."""
    db = AsyncMock()
    db.flush = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # _get_project
            result.scalar_one_or_none.return_value = project
        elif call_count == 2:
            # _get_gate
            result.scalar_one_or_none.return_value = gate
        elif call_count == 3:
            # process_decision: fetch agent_run
            result.scalar_one.return_value = agent_run
        elif call_count == 4:
            # process_decision: fetch project
            result.scalar_one.return_value = project_after or project
        elif call_count == 5:
            # auto-start: fetch completed_run to determine next agent
            result.scalar_one.return_value = agent_run
        elif call_count == 6:
            # re-fetch project after process_decision
            result.scalar_one.return_value = project_after or project
        else:
            # Additional queries from auto-start (new agent run, etc.)
            result.scalar_one.return_value = project_after or project
            result.scalar_one_or_none.return_value = project_after or project
        return result

    db.execute = AsyncMock(side_effect=fake_execute)
    db.refresh = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


# ─── GET /approvals ───


@pytest.mark.asyncio
async def test_list_approvals_empty() -> None:
    """List approvals returns empty list for project with no gates."""
    db = _mock_db_for_list(_make_project(), [], 0)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/projects/{PROJECT_ID}/approvals/")

    assert resp.status_code == 200
    data = resp.json()
    assert data["approvals"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_approvals_with_gates() -> None:
    """List approvals returns gates with correct structure."""
    gate = _make_gate()
    db = _mock_db_for_list(_make_project(), [gate], 1)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/projects/{PROJECT_ID}/approvals/")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["approvals"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_approvals_project_not_found() -> None:
    """List approvals returns 404 for missing project."""
    db = _mock_db_for_list(None, [], 0)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/projects/{PROJECT_ID}/approvals/")

    assert resp.status_code == 404


# ─── GET /approvals/{gate_id} ───


@pytest.mark.asyncio
async def test_get_approval_detail() -> None:
    """Get approval returns gate with agent run output."""
    gate = _make_gate()
    run = _make_agent_run(output_summary={"findings": {"rules": [1, 2]}})
    db = _mock_db_for_detail(_make_project(), gate, run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["agent_type"] == "discover"
    assert data["output_summary"]["findings"]["rules"] == [1, 2]


@pytest.mark.asyncio
async def test_get_approval_not_found() -> None:
    """Get approval returns 404 for missing gate."""
    db = _mock_db_for_detail(_make_project(), gate=None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}"
        )

    assert resp.status_code == 404


# ─── POST /approvals/{gate_id}/decide ───


@pytest.mark.asyncio
async def test_decide_approve() -> None:
    """Approving advances project and returns success message."""
    gate = _make_gate()
    run = _make_agent_run()
    project = _make_project(status=ProjectStatus.DISCOVER)
    project_after = _make_project(status=ProjectStatus.DESIGN)
    db = _mock_db_for_decide(project, gate, run, project_after)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}/decide",
            json={"status": "approved", "reviewer_notes": "Ship it"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["project_status"] == "design"
    assert "Approved" in data["message"]


@pytest.mark.asyncio
async def test_decide_reject() -> None:
    """Rejecting returns rejection message."""
    gate = _make_gate()
    run = _make_agent_run()
    project = _make_project(status=ProjectStatus.DISCOVER)
    db = _mock_db_for_decide(project, gate, run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}/decide",
            json={"status": "rejected", "reviewer_notes": "Incomplete"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert "Rejected" in data["message"]


@pytest.mark.asyncio
async def test_decide_revision_requested() -> None:
    """Requesting revision re-triggers discovery and returns appropriate message."""
    gate = _make_gate()
    run = _make_agent_run(output_summary={"findings": {}})
    run.input_context = {"document_text": "sample text"}
    project = _make_project()

    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # _get_project
            result.scalar_one_or_none.return_value = project
        elif call_count == 2:
            # _get_gate
            result.scalar_one_or_none.return_value = gate
        elif call_count == 3:
            # process_decision: fetch agent_run
            result.scalar_one.return_value = run
        elif call_count == 4:
            # process_decision: fetch project
            result.scalar_one.return_value = project
        elif call_count == 5:
            # revision_requested: fetch original agent_run
            result.scalar_one.return_value = run
        elif call_count == 6:
            # re-fetch project after process_decision
            result.scalar_one.return_value = project
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.approvals.asyncio.create_task"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}/decide",
                json={"status": "revision_requested", "reviewer_notes": "Expand auth section"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "revision_requested"
    assert "Revision" in data["message"]


@pytest.mark.asyncio
async def test_decide_already_decided() -> None:
    """Deciding on an already-decided gate returns 409."""
    gate = _make_gate(status=ApprovalStatus.APPROVED)
    db = _mock_db_for_detail(_make_project(), gate)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}/decide",
            json={"status": "approved"},
        )

    assert resp.status_code == 409
    assert "already decided" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_decide_pending_status_rejected() -> None:
    """Setting status to 'pending' is rejected with 422."""
    gate = _make_gate()
    db = _mock_db_for_detail(_make_project(), gate)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}/decide",
            json={"status": "pending"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_decide_gate_not_found() -> None:
    """Deciding on missing gate returns 404."""
    db = _mock_db_for_detail(_make_project(), gate=None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/approvals/{GATE_ID}/decide",
            json={"status": "approved"},
        )

    assert resp.status_code == 404