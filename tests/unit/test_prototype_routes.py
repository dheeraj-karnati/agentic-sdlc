"""Unit tests for Prototype Agent API routes."""

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
    Artifact,
    ArtifactType,
    Project,
    ProjectStatus,
    RunStatus,
)


# ─── Constants ───

PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
RUN_ID = uuid.UUID("00000000-0000-0000-0000-000000000088")


# ─── Factories ───


def _make_project(status: ProjectStatus = ProjectStatus.PROTOTYPE) -> MagicMock:
    p = MagicMock(spec=Project)
    p.id = PROJECT_ID
    p.name = "Test"
    p.status = status
    return p


def _make_agent_run(
    status: RunStatus = RunStatus.COMPLETED,
    agent_type: AgentType = AgentType.PROTOTYPE,
    output_summary: dict | None = None,
) -> MagicMock:
    run = MagicMock(spec=AgentRun)
    run.id = RUN_ID
    run.project_id = PROJECT_ID
    run.agent_type = agent_type
    run.status = status
    run.output_summary = output_summary or {"prototype": {}, "artifacts_stored": 0}
    run.error_details = None
    run.started_at = datetime.now(timezone.utc)
    run.completed_at = None
    run.created_at = datetime.now(timezone.utc)
    return run


def _make_artifact(name: str = "Prototype Page Component") -> MagicMock:
    a = MagicMock(spec=Artifact)
    a.id = uuid.uuid4()
    a.project_id = PROJECT_ID
    a.agent_run_id = RUN_ID
    a.type = ArtifactType.PROTOTYPE
    a.name = name
    a.content = "'use client';\nexport default function App() { return <div>Hello</div>; }"
    a.version = 1
    a.metadata_ = {"section": "page_code", "source_agent": "prototype"}
    a.created_at = datetime.now(timezone.utc)
    return a


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


# ─── POST /agents/prototype/start ───


@pytest.mark.asyncio
async def test_start_prototype_creates_run() -> None:
    """Starting prototype agent creates a run and returns 201."""
    project = _make_project(status=ProjectStatus.PROTOTYPE)
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    async def fake_refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:  # type: ignore[union-attr]
            obj.id = RUN_ID  # type: ignore[union-attr]

    db.refresh = AsyncMock(side_effect=fake_refresh)

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.agents.asyncio.create_task"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/agents/prototype/start",
                json={},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert "Prototype agent started" in data["message"]


@pytest.mark.asyncio
async def test_start_prototype_wrong_status() -> None:
    """Starting prototype agent fails if project is not in 'prototype' status."""
    project = _make_project(status=ProjectStatus.DESIGN)
    db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/prototype/start",
            json={},
        )

    assert resp.status_code == 409
    assert "prototype" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_start_prototype_with_reviewer_notes() -> None:
    """Starting prototype agent passes reviewer notes to the agent run."""
    project = _make_project(status=ProjectStatus.PROTOTYPE)
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    async def fake_refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:  # type: ignore[union-attr]
            obj.id = RUN_ID  # type: ignore[union-attr]

    db.refresh = AsyncMock(side_effect=fake_refresh)

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.agents.asyncio.create_task"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/agents/prototype/start",
                json={"reviewer_notes": "Add dark mode toggle"},
            )

    assert resp.status_code == 201
    # Verify the agent run was created with reviewer notes
    add_call = db.add.call_args[0][0]
    assert add_call.input_context["reviewer_notes"] == "Add dark mode toggle"


@pytest.mark.asyncio
async def test_start_prototype_project_not_found() -> None:
    """Starting prototype agent returns 404 for missing project."""
    db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/prototype/start",
            json={},
        )

    assert resp.status_code == 404


# ─── GET /agents/{run_id}/prototype-output ───


@pytest.mark.asyncio
async def test_get_prototype_output() -> None:
    """Get demo output returns run with artifacts."""
    project = _make_project()
    run = _make_agent_run(
        output_summary={
            "prototype": {"page_code": "export default function App() {}"},
            "artifacts_stored": 4,
        }
    )
    artifacts = [_make_artifact("Page Component"), _make_artifact("Mock Data")]

    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        elif call_count == 2:
            result.scalar_one_or_none.return_value = run
        else:
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = artifacts
            result.scalars.return_value = scalars_mock
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/prototype-output"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_type"] == "prototype"
    assert "page_code" in data["prototype"]
    assert len(data["artifacts"]) == 2


@pytest.mark.asyncio
async def test_get_prototype_output_not_found() -> None:
    """Get demo output returns 404 for missing run."""
    project = _make_project()
    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        else:
            result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/prototype-output"
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_prototype_output_with_errors() -> None:
    """Get demo output includes error details when agent failed."""
    project = _make_project()
    run = _make_agent_run(status=RunStatus.FAILED)
    run.error_details = "LLM timeout"
    run.output_summary = {}

    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        elif call_count == 2:
            result.scalar_one_or_none.return_value = run
        else:
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            result.scalars.return_value = scalars_mock
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/prototype-output"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert "LLM timeout" in data["errors"]


# ─── POST /agents/{run_id}/feedback ───

NEW_RUN_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _setup_feedback_db(
    project: MagicMock,
    run: MagicMock,
    prior_feedback: list[str] | None = None,
    max_version: int = 1,
) -> AsyncMock:
    """Create a mock db for feedback tests with predictable call routing."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    async def fake_refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:  # type: ignore[union-attr]
            obj.id = NEW_RUN_ID  # type: ignore[union-attr]

    db.refresh = AsyncMock(side_effect=fake_refresh)

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # _get_project
            result.scalar_one_or_none.return_value = project
        elif call_count == 2:
            # _get_agent_run
            result.scalar_one_or_none.return_value = run
        elif call_count == 3:
            # Prior feedback conversation query
            rows = [(f,) for f in (prior_feedback or [])]
            result.all.return_value = rows
        elif call_count == 4:
            # Max version query
            result.scalar_one_or_none.return_value = max_version
        return result

    db.execute = AsyncMock(side_effect=fake_execute)
    return db


@pytest.mark.asyncio
async def test_feedback_creates_conversation_and_new_run() -> None:
    """Feedback stores a conversation and creates a new agent run."""
    project = _make_project()
    run = _make_agent_run(
        status=RunStatus.PAUSED_FOR_APPROVAL,
        output_summary={"prototype": {"page_code": "old code"}, "artifacts_stored": 4},
    )
    db = _setup_feedback_db(project, run, prior_feedback=[], max_version=1)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.agents.asyncio.create_task") as mock_task:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/feedback",
                json={"feedback": "Make the navigation sidebar collapsible"},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["version"] == 2
    assert "Feedback received" in data["message"]

    # Verify conversation was stored (first add call)
    add_calls = [call[0][0] for call in db.add.call_args_list]
    from src.context_store.models import Conversation, MessageDirection
    conv_calls = [c for c in add_calls if isinstance(c, Conversation)]
    assert len(conv_calls) == 1
    assert conv_calls[0].direction == MessageDirection.USER_TO_AGENT
    assert conv_calls[0].message == "Make the navigation sidebar collapsible"

    # Verify new agent run was created (second add call)
    run_calls = [c for c in add_calls if isinstance(c, AgentRun)]
    assert len(run_calls) == 1
    assert run_calls[0].agent_type == AgentType.PROTOTYPE
    assert run_calls[0].input_context["feedback"] == "Make the navigation sidebar collapsible"
    assert run_calls[0].input_context["version"] == 2

    # Verify background task was launched
    mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_feedback_accumulates_history() -> None:
    """Feedback gathers prior feedback and appends current for cumulative context."""
    project = _make_project()
    run = _make_agent_run(
        status=RunStatus.COMPLETED,
        output_summary={"prototype": {"page_code": "v2 code"}},
    )
    prior = ["Add dark mode", "Fix navigation"]
    db = _setup_feedback_db(project, run, prior_feedback=prior, max_version=2)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.agents.asyncio.create_task") as mock_task:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/feedback",
                json={"feedback": "Add loading spinners"},
            )

    assert resp.status_code == 201
    assert resp.json()["version"] == 3  # max_version=2, so next is 3

    # Check background task was called with accumulated feedback
    task_args = mock_task.call_args[0][0]
    # The coroutine args can be inspected via the AgentRun input_context
    add_calls = [call[0][0] for call in db.add.call_args_list]
    run_calls = [c for c in add_calls if isinstance(c, AgentRun)]
    assert len(run_calls) == 1
    history = run_calls[0].input_context["feedback_history"]
    assert history == ["Add dark mode", "Fix navigation", "Add loading spinners"]


@pytest.mark.asyncio
async def test_feedback_rejects_non_prototype_run() -> None:
    """Feedback returns 409 for non-prototype agent runs."""
    project = _make_project()
    run = _make_agent_run(agent_type=AgentType.DESIGN, status=RunStatus.COMPLETED)

    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        else:
            result.scalar_one_or_none.return_value = run
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/feedback",
            json={"feedback": "Some feedback"},
        )

    assert resp.status_code == 409
    assert "prototype" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_feedback_rejects_wrong_status() -> None:
    """Feedback returns 409 if run is not completed or paused_for_approval."""
    project = _make_project()
    run = _make_agent_run(status=RunStatus.RUNNING)

    db = AsyncMock()
    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = project
        else:
            result.scalar_one_or_none.return_value = run
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/feedback",
            json={"feedback": "Some feedback"},
        )

    assert resp.status_code == 409
    assert "completed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_feedback_rejects_empty_feedback() -> None:
    """Feedback returns 422 if feedback text is empty."""
    project = _make_project()
    db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/feedback",
            json={"feedback": ""},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_feedback_passes_previous_demo() -> None:
    """Feedback task receives the previous demo for cumulative iteration."""
    project = _make_project()
    prev_proto = {"page_code": "function App() {}", "mock_data": "const data = [];"}
    run = _make_agent_run(
        status=RunStatus.PAUSED_FOR_APPROVAL,
        output_summary={"prototype": prev_proto, "artifacts_stored": 4},
    )
    db = _setup_feedback_db(project, run, prior_feedback=[], max_version=1)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with patch("src.api.routes.agents.asyncio.create_task") as mock_task:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/feedback",
                json={"feedback": "Add dark mode toggle"},
            )

    assert resp.status_code == 201

    # Verify the background task coroutine was called with previous_demo
    coro = mock_task.call_args[0][0]
    # The coro is _run_prototype_feedback_graph(run_id, project_id, previous_demo, ...)
    # We can check the AgentRun input_context instead
    add_calls = [call[0][0] for call in db.add.call_args_list]
    run_calls = [c for c in add_calls if isinstance(c, AgentRun)]
    assert run_calls[0].input_context["parent_run_id"] == str(RUN_ID)