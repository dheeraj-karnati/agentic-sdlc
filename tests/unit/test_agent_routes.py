"""Unit tests for agent API routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.context_store.database import get_db
from src.context_store.models import AgentRun, AgentType, Project, RunStatus


# ─── Constants ───

PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
RUN_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


# ─── Factories ───


def _make_project() -> MagicMock:
    p = MagicMock(spec=Project)
    p.id = PROJECT_ID
    p.name = "Test Project"
    return p


def _make_agent_run(
    status: RunStatus = RunStatus.PENDING,
    output_summary: dict | None = None,
    input_context: dict | None = None,
    error_details: str | None = None,
) -> MagicMock:
    run = MagicMock(spec=AgentRun)
    run.id = RUN_ID
    run.project_id = PROJECT_ID
    run.agent_type = AgentType.DISCOVER
    run.status = status
    run.input_context = input_context or {"document_text": "test doc"}
    run.output_summary = output_summary or {}
    run.error_details = error_details
    run.token_usage = {}
    run.started_at = datetime.now(timezone.utc)
    run.completed_at = None
    run.created_at = datetime.now(timezone.utc)
    return run


def _mock_db(project: MagicMock | None, agent_run: MagicMock | None = None) -> AsyncMock:
    """Create a mock db session that returns project on 1st query, agent_run on 2nd."""
    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        else:
            result.scalar_one_or_none.return_value = agent_run
        return result

    db.execute = AsyncMock(side_effect=fake_execute)
    db.add = MagicMock()
    db.flush = AsyncMock()

    async def refresh_side_effect(obj):
        if isinstance(obj, AgentRun) and obj.id is None:
            obj.id = RUN_ID

    db.refresh = AsyncMock(side_effect=refresh_side_effect)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    """Ensure dependency overrides are cleaned up after each test."""
    yield
    app.dependency_overrides.clear()


# ─── POST /discovery/start ───


@pytest.mark.asyncio
async def test_start_discovery_creates_run() -> None:
    """POST /discovery/start creates an agent_run and returns run_id."""
    project = _make_project()
    db = _mock_db(project)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.agents.asyncio") as mock_asyncio:
        mock_asyncio.create_task = MagicMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/agents/discovery/start",
                json={"document_text": "Legacy system uses Oracle DB."},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "pending"
    assert data["message"] == "Discovery agent started"
    db.add.assert_called_once()
    mock_asyncio.create_task.assert_called_once()


@pytest.mark.asyncio
async def test_start_discovery_project_not_found() -> None:
    """POST /discovery/start returns 404 if project doesn't exist."""
    db = _mock_db(project=None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/discovery/start",
            json={"document_text": "some text"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_discovery_empty_text() -> None:
    """POST /discovery/start returns 422 for empty document_text."""
    db = _mock_db(_make_project())

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/discovery/start",
            json={"document_text": ""},
        )

    assert resp.status_code == 422


# ─── GET /{run_id}/status ───


@pytest.mark.asyncio
async def test_get_status_completed() -> None:
    """GET /status returns findings and completed status."""
    output = {
        "findings": {"business_rules": [{"title": "R1", "description": "desc"}]},
        "stored_count": 1,
        "is_clear": True,
        "questions": [],
    }
    run = _make_agent_run(status=RunStatus.COMPLETED, output_summary=output)
    run.completed_at = datetime.now(timezone.utc)
    db = _mock_db(_make_project(), run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/status"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["pending_questions"] == []
    assert data["output_summary"]["stored_count"] == 1


@pytest.mark.asyncio
async def test_get_status_paused_with_questions() -> None:
    """GET /status returns pending questions when paused_for_input."""
    questions = [
        {"finding_title": "Auth", "question": "Which LDAP?", "reason": "Not specified"}
    ]
    output = {"findings": {}, "is_clear": False, "questions": questions}
    run = _make_agent_run(status=RunStatus.PAUSED_FOR_INPUT, output_summary=output)
    db = _mock_db(_make_project(), run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/status"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "paused_for_input"
    assert len(data["pending_questions"]) == 1
    assert data["pending_questions"][0]["question"] == "Which LDAP?"


@pytest.mark.asyncio
async def test_get_status_run_not_found() -> None:
    """GET /status returns 404 for unknown run_id."""
    db = _mock_db(_make_project(), agent_run=None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/status"
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_status_with_errors() -> None:
    """GET /status includes errors when agent run has failed."""
    run = _make_agent_run(status=RunStatus.FAILED, error_details="LLM API timeout")
    db = _mock_db(_make_project(), run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/status"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert "LLM API timeout" in data["errors"]


# ─── POST /{run_id}/respond ───


@pytest.mark.asyncio
async def test_respond_accepts_answers() -> None:
    """POST /respond accepts user answers and resumes the agent."""
    run = _make_agent_run(
        status=RunStatus.PAUSED_FOR_INPUT,
        input_context={"document_text": "test doc"},
    )
    db = _mock_db(_make_project(), run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.agents.asyncio") as mock_asyncio:
        mock_asyncio.create_task = MagicMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/respond",
                json={
                    "answers": [
                        {"question": "Which LDAP?", "answer": "Corporate AD on ldap.corp.com"}
                    ]
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["message"] == "Responses received, agent resuming"
    mock_asyncio.create_task.assert_called_once()


@pytest.mark.asyncio
async def test_respond_wrong_status() -> None:
    """POST /respond returns 409 if agent is not paused_for_input."""
    run = _make_agent_run(status=RunStatus.RUNNING)
    db = _mock_db(_make_project(), run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/respond",
            json={"answers": [{"question": "Q", "answer": "A"}]},
        )

    assert resp.status_code == 409
    assert "not awaiting input" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_respond_empty_answers() -> None:
    """POST /respond returns 422 for empty answers list."""
    run = _make_agent_run(status=RunStatus.PAUSED_FOR_INPUT)
    db = _mock_db(_make_project(), run)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/respond",
            json={"answers": []},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_respond_run_not_found() -> None:
    """POST /respond returns 404 for unknown run_id."""
    db = _mock_db(_make_project(), agent_run=None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/respond",
            json={"answers": [{"question": "Q", "answer": "A"}]},
        )

    assert resp.status_code == 404