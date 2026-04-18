"""Unit tests for the Plan routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routes.plan import router
from src.context_store.database import get_db
from src.context_store.models import (
    AgentType,
    EpicStatus,
    ProjectStatus,
    RunStatus,
    StoryStatus,
)


# ─── Test App Setup ───


app = FastAPI()
app.include_router(router, prefix="/api")

PROJECT_ID = uuid.uuid4()
RUN_ID = uuid.uuid4()
EPIC_ID = uuid.uuid4()
STORY_ID = uuid.uuid4()


def _mock_project(status: ProjectStatus = ProjectStatus.PLAN) -> MagicMock:
    p = MagicMock()
    p.id = PROJECT_ID
    p.status = status
    return p


def _mock_epic(**kwargs) -> MagicMock:
    e = MagicMock()
    e.id = kwargs.get("id", EPIC_ID)
    e.project_id = PROJECT_ID
    e.agent_run_id = RUN_ID
    e.title = kwargs.get("title", "Auth Epic")
    e.description = kwargs.get("description", "Authentication")
    e.priority = kwargs.get("priority", 1)
    e.sequence_order = kwargs.get("sequence_order", 1)
    e.status = kwargs.get("status", EpicStatus.DRAFT)
    e.metadata_ = {}
    e.created_at = datetime.now(timezone.utc)
    e.updated_at = datetime.now(timezone.utc)
    return e


def _mock_story(**kwargs) -> MagicMock:
    s = MagicMock()
    s.id = kwargs.get("id", STORY_ID)
    s.epic_id = kwargs.get("epic_id", EPIC_ID)
    s.project_id = PROJECT_ID
    s.title = kwargs.get("title", "Login Page")
    s.description = kwargs.get("description", "As a user I want to log in")
    s.acceptance_criteria = kwargs.get("acceptance_criteria", ["Given valid creds"])
    s.story_points = kwargs.get("story_points", 3)
    s.priority = kwargs.get("priority", 1)
    s.sequence_order = kwargs.get("sequence_order", 1)
    s.status = kwargs.get("status", StoryStatus.DRAFT)
    s.technical_notes = kwargs.get("technical_notes", "JWT")
    s.schema_changes = kwargs.get("schema_changes", None)
    s.api_endpoints = kwargs.get("api_endpoints", [])
    s.ui_components = kwargs.get("ui_components", [])
    s.dependencies = kwargs.get("dependencies", [])
    s.metadata_ = {}
    s.created_at = datetime.now(timezone.utc)
    s.updated_at = datetime.now(timezone.utc)
    return s


def _mock_run(
    agent_type: AgentType = AgentType.PLAN,
    status: RunStatus = RunStatus.COMPLETED,
) -> MagicMock:
    r = MagicMock()
    r.id = RUN_ID
    r.project_id = PROJECT_ID
    r.agent_type = agent_type
    r.status = status
    r.input_context = {}
    r.output_summary = {"epics_count": 2, "stories_count": 5}
    r.error_details = None
    r.started_at = datetime.now(timezone.utc)
    r.completed_at = datetime.now(timezone.utc)
    return r


# ─── Start Define Tests ───


class TestStartPlan:
    @pytest.mark.asyncio
    async def test_start_success(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project()
        mock_agent_run = MagicMock()
        mock_agent_run.id = RUN_ID
        mock_agent_run.status = RunStatus.PENDING

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=project))
        )
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            obj.id = RUN_ID

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        with patch("src.api.routes.plan.asyncio.create_task"):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    f"/api/projects/{PROJECT_ID}/plan/start",
                    json={},
                )

        app.dependency_overrides.clear()
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"] == "Plan agent started"

    @pytest.mark.asyncio
    async def test_start_wrong_status(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project(status=ProjectStatus.DESIGN)

        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=project))
        )

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                f"/api/projects/{PROJECT_ID}/plan/start",
                json={},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_start_project_not_found(self) -> None:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                f"/api/projects/{PROJECT_ID}/plan/start",
                json={},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 404


# ─── Epic CRUD Tests ───


class TestEpicEndpoints:
    @pytest.mark.asyncio
    async def test_list_epics(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project()
        epic = _mock_epic()

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=project))
            else:
                return MagicMock(
                    scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[epic])))
                )

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(f"/api/projects/{PROJECT_ID}/plan/epics")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Auth Epic"

    @pytest.mark.asyncio
    async def test_update_epic(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project()
        epic = _mock_epic()

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=project))
            else:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=epic))

        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.put(
                f"/api/projects/{PROJECT_ID}/plan/epics/{EPIC_ID}",
                json={"title": "Updated Auth"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200


# ─── Story CRUD Tests ───


class TestStoryEndpoints:
    @pytest.mark.asyncio
    async def test_create_story(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project()
        epic = _mock_epic()
        created_story = _mock_story()

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return MagicMock(scalar_one_or_none=MagicMock(
                    return_value=project if call_count == 1 else epic
                ))
            else:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=0))

        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            # Populate the UserStory with mock values for response serialization
            obj.id = created_story.id
            obj.epic_id = EPIC_ID
            obj.project_id = PROJECT_ID
            obj.title = "New Story"
            obj.description = "As a user..."
            obj.acceptance_criteria = []
            obj.story_points = None
            obj.priority = 0
            obj.sequence_order = 1
            obj.status = StoryStatus.DRAFT
            obj.technical_notes = None
            obj.schema_changes = None
            obj.api_endpoints = []
            obj.ui_components = []
            obj.dependencies = []
            obj.metadata_ = {}
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                f"/api/projects/{PROJECT_ID}/plan/stories",
                json={
                    "epic_id": str(EPIC_ID),
                    "title": "New Story",
                    "description": "As a user...",
                },
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Story"

    @pytest.mark.asyncio
    async def test_delete_story(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project()
        story = _mock_story()

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=project))
            elif call_count == 2:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=story))
            else:
                return MagicMock(
                    scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
                )

        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.delete = AsyncMock()
        mock_db.flush = AsyncMock()

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.delete(
                f"/api/projects/{PROJECT_ID}/plan/stories/{STORY_ID}"
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_resequence_stories(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project()
        s1_id = uuid.uuid4()
        s2_id = uuid.uuid4()
        story1 = _mock_story(id=s1_id, sequence_order=1)
        story2 = _mock_story(id=s2_id, sequence_order=2)

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=project))
            elif call_count == 2:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=story1))
            else:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=story2))

        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.flush = AsyncMock()

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                f"/api/projects/{PROJECT_ID}/plan/stories/resequence",
                json={
                    "stories": [
                        {"id": str(s1_id), "sequence_order": 2},
                        {"id": str(s2_id), "sequence_order": 1},
                    ]
                },
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert "Resequenced" in data["message"]

    @pytest.mark.asyncio
    async def test_list_stories(self) -> None:
        mock_db = AsyncMock()
        project = _mock_project()
        story = _mock_story()

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=project))
            else:
                return MagicMock(
                    scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[story])))
                )

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        async def get_test_db():
            yield mock_db

        app.dependency_overrides[get_db] = get_test_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(f"/api/projects/{PROJECT_ID}/plan/stories")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Login Page"