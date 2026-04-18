"""Unit tests for Design Agent API routes."""

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
RUN_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


# ─── Factories ───


def _make_project(status: ProjectStatus = ProjectStatus.DESIGN) -> MagicMock:
    p = MagicMock(spec=Project)
    p.id = PROJECT_ID
    p.name = "Test"
    p.status = status
    return p


def _make_agent_run(
    status: RunStatus = RunStatus.COMPLETED,
    agent_type: AgentType = AgentType.DESIGN,
    output_summary: dict | None = None,
) -> MagicMock:
    run = MagicMock(spec=AgentRun)
    run.id = RUN_ID
    run.project_id = PROJECT_ID
    run.agent_type = agent_type
    run.status = status
    run.output_summary = output_summary or {"design": {}, "artifacts_stored": 0}
    run.error_details = None
    run.started_at = datetime.now(timezone.utc)
    run.completed_at = None
    run.created_at = datetime.now(timezone.utc)
    return run


def _make_artifact(name: str = "Architecture Recommendation") -> MagicMock:
    a = MagicMock(spec=Artifact)
    a.id = uuid.uuid4()
    a.project_id = PROJECT_ID
    a.agent_run_id = RUN_ID
    a.type = ArtifactType.DOCUMENT
    a.name = name
    a.content = '{"recommendation": "modular_monolith"}'
    a.version = 1
    a.metadata_ = {"section": "architecture"}
    a.created_at = datetime.now(timezone.utc)
    return a


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


# ─── POST /agents/design/start ───


@pytest.mark.asyncio
async def test_start_design_creates_run() -> None:
    """Starting design agent creates a run and returns 201."""
    project = _make_project(status=ProjectStatus.DESIGN)
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
                f"/api/projects/{PROJECT_ID}/agents/design/start",
                json={},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert "Design agent started" in data["message"]


@pytest.mark.asyncio
async def test_start_design_wrong_status() -> None:
    """Starting design agent fails if project is not in 'design' status."""
    project = _make_project(status=ProjectStatus.DISCOVER)
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
            f"/api/projects/{PROJECT_ID}/agents/design/start",
            json={},
        )

    assert resp.status_code == 409
    assert "design" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_start_design_with_reviewer_notes() -> None:
    """Starting design agent passes reviewer notes to the agent run."""
    project = _make_project(status=ProjectStatus.DESIGN)
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
                f"/api/projects/{PROJECT_ID}/agents/design/start",
                json={"reviewer_notes": "Expand auth section"},
            )

    assert resp.status_code == 201
    # Verify the agent run was created with reviewer notes
    add_call = db.add.call_args[0][0]
    assert add_call.input_context["reviewer_notes"] == "Expand auth section"


# ─── GET /agents/{run_id}/design-output ───


@pytest.mark.asyncio
async def test_get_design_output() -> None:
    """Get design output returns run with artifacts."""
    project = _make_project()
    run = _make_agent_run(
        output_summary={
            "design": {"architecture": {"recommendation": "monolith"}},
            "artifacts_stored": 3,
        }
    )
    artifacts = [_make_artifact("Arch"), _make_artifact("Schema")]

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
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/design-output"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_type"] == "design"
    assert data["design"]["architecture"]["recommendation"] == "monolith"
    assert len(data["artifacts"]) == 2


@pytest.mark.asyncio
async def test_get_design_output_not_found() -> None:
    """Get design output returns 404 for missing run."""
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
            f"/api/projects/{PROJECT_ID}/agents/{RUN_ID}/design-output"
        )

    assert resp.status_code == 404