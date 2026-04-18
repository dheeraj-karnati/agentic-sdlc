"""Unit tests for the Define Agent (artifact-first approach)."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.plan.agent import (
    PlanState,
    build_plan_graph,
    create_initial_state,
    gather_context,
    generate_plan,
    import_plan_to_db,
    store_artifact,
    topological_sort_stories,
    validate_plan,
)


# ─── Fixtures ───


def _make_state(**overrides) -> PlanState:
    """Create a PlanState with defaults."""
    defaults = create_initial_state(
        project_id=str(uuid.uuid4()),
        agent_run_id=str(uuid.uuid4()),
    )
    defaults.update(overrides)
    return defaults


SAMPLE_PLAN = {
    "epics": [
        {
            "title": "Auth",
            "description": "Authentication system",
            "priority": 1,
            "stories": [
                {
                    "title": "Login Page",
                    "description": "As a user I want to log in",
                    "acceptance_criteria": ["Given valid creds"],
                    "story_points": 3,
                    "priority": 1,
                    "technical_notes": "Use JWT",
                    "schema_changes": None,
                    "api_endpoints": [{"method": "POST", "path": "/auth/login", "description": "Login"}],
                    "ui_components": [{"name": "LoginForm", "purpose": "Auth form"}],
                    "dependencies": [],
                },
                {
                    "title": "Registration",
                    "description": "As a user I want to register",
                    "acceptance_criteria": ["Given valid email"],
                    "story_points": 5,
                    "priority": 2,
                    "technical_notes": "Email verification",
                    "schema_changes": "CREATE TABLE users",
                    "api_endpoints": [],
                    "ui_components": [],
                    "dependencies": ["Login Page"],
                },
            ],
        },
        {
            "title": "Dashboard",
            "description": "Main dashboard",
            "priority": 2,
            "stories": [
                {
                    "title": "Overview Widget",
                    "description": "As a user I want to see overview",
                    "acceptance_criteria": ["Given logged in"],
                    "story_points": 3,
                    "priority": 1,
                    "technical_notes": "React component",
                    "schema_changes": None,
                    "api_endpoints": [],
                    "ui_components": [{"name": "Overview", "purpose": "Dashboard widget"}],
                    "dependencies": ["Login Page"],
                },
            ],
        },
    ]
}


# ─── create_initial_state tests ───


class TestCreateInitialState:
    def test_default_state(self) -> None:
        state = create_initial_state(project_id="abc")
        assert state["project_id"] == "abc"
        assert state["agent_run_id"] == ""
        assert state["reviewer_notes"] == ""
        assert state["plan"] == {}
        assert state["errors"] == []
        assert state["plan_artifact_id"] is None

    def test_with_reviewer_notes(self) -> None:
        state = create_initial_state(
            project_id="abc", reviewer_notes="fix priority"
        )
        assert state["reviewer_notes"] == "fix priority"

    def test_with_injected_deps(self) -> None:
        mock_llm = MagicMock()
        mock_session = MagicMock()
        state = create_initial_state(
            project_id="abc", llm=mock_llm, session=mock_session
        )
        assert state["_llm"] is mock_llm
        assert state["_session"] is mock_session


# ─── gather_context tests ───


class TestGatherContext:
    @pytest.mark.asyncio
    async def test_no_session(self) -> None:
        state = _make_state(_session=None)
        result = await gather_context(state)
        assert "No database session provided" in result["errors"]

    @pytest.mark.asyncio
    async def test_loads_artifacts(self) -> None:
        mock_design = MagicMock()
        mock_design.name = "Architecture"
        mock_design.type = MagicMock(value="document")
        mock_design.content = "arch content"
        mock_design.metadata_ = {"source_agent": "design"}

        mock_biz = MagicMock()
        mock_biz.category = "requirements"
        mock_biz.title = "Auth"
        mock_biz.content = "auth context"

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_design])))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_biz])))),
            ]
        )

        state = _make_state(_session=session)
        result = await gather_context(state)

        assert len(result["design_artifacts"]) == 1
        assert result["design_artifacts"][0]["name"] == "Architecture"
        assert len(result["business_context"]) == 1

    @pytest.mark.asyncio
    async def test_handles_db_error(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=Exception("DB connection lost"))

        state = _make_state(_session=session)
        result = await gather_context(state)
        assert any("gather_context failed" in e for e in result["errors"])


# ─── generate_plan tests ───


class TestGeneratePlan:
    @pytest.mark.asyncio
    async def test_no_artifacts(self) -> None:
        state = _make_state(design_artifacts=[], prototype_artifacts=[])
        result = await generate_plan(state)
        assert result["plan"] == {}
        assert any("No design or prototype" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_generates_plan(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content=json.dumps(SAMPLE_PLAN))
        )

        state = _make_state(
            design_artifacts=[{"name": "Arch", "content": "design"}],
            _llm=mock_llm,
        )
        result = await generate_plan(state)

        plan = result["plan"]
        assert len(plan["epics"]) == 2
        assert plan["epics"][0]["title"] == "Auth"
        assert plan["epics"][0]["sequence_order"] == 1
        assert len(plan["epics"][0]["stories"]) == 2

    @pytest.mark.asyncio
    async def test_handles_json_in_code_block(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content=f'```json\n{json.dumps(SAMPLE_PLAN)}\n```'
            )
        )

        state = _make_state(
            design_artifacts=[{"name": "Arch", "content": "design"}],
            _llm=mock_llm,
        )
        result = await generate_plan(state)
        assert len(result["plan"]["epics"]) == 2

    @pytest.mark.asyncio
    async def test_handles_bare_array(self) -> None:
        """LLM returns a bare array of epics without wrapper object."""
        epics_array = SAMPLE_PLAN["epics"]
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content=json.dumps(epics_array))
        )

        state = _make_state(
            design_artifacts=[{"name": "Arch", "content": "design"}],
            _llm=mock_llm,
        )
        result = await generate_plan(state)
        assert len(result["plan"]["epics"]) == 2

    @pytest.mark.asyncio
    async def test_handles_llm_error(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("API error"))

        state = _make_state(
            design_artifacts=[{"name": "Arch", "content": "design"}],
            _llm=mock_llm,
        )
        result = await generate_plan(state)
        assert result["plan"] == {}
        assert any("generate_plan failed" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_sets_default_fields(self) -> None:
        """Stories missing optional fields get defaults."""
        minimal_plan = {
            "epics": [{
                "title": "E1",
                "description": "Epic 1",
                "priority": 1,
                "stories": [{"title": "S1", "description": "Story 1", "priority": 1, "story_points": 2}],
            }]
        }
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content=json.dumps(minimal_plan))
        )

        state = _make_state(
            design_artifacts=[{"name": "Arch", "content": "design"}],
            _llm=mock_llm,
        )
        result = await generate_plan(state)
        story = result["plan"]["epics"][0]["stories"][0]
        assert story["acceptance_criteria"] == []
        assert story["dependencies"] == []
        assert story["api_endpoints"] == []
        assert story["ui_components"] == []


# ─── topological_sort_stories tests ───


class TestTopologicalSortStories:
    def test_empty_plan(self) -> None:
        assert topological_sort_stories({}) == []
        assert topological_sort_stories({"epics": []}) == []

    def test_respects_dependencies(self) -> None:
        plan = {
            "epics": [{
                "title": "E1",
                "stories": [
                    {"title": "B", "priority": 1, "dependencies": ["A"]},
                    {"title": "A", "priority": 2, "dependencies": []},
                    {"title": "C", "priority": 3, "dependencies": ["B"]},
                ],
            }]
        }
        sorted_stories = topological_sort_stories(plan)
        titles = [s["title"] for s in sorted_stories]
        assert titles.index("A") < titles.index("B")
        assert titles.index("B") < titles.index("C")

    def test_assigns_sequence_order(self) -> None:
        plan = {
            "epics": [{
                "title": "E1",
                "stories": [
                    {"title": "X", "priority": 1, "dependencies": []},
                    {"title": "Y", "priority": 2, "dependencies": []},
                ],
            }]
        }
        sorted_stories = topological_sort_stories(plan)
        assert sorted_stories[0]["sequence_order"] == 1
        assert sorted_stories[1]["sequence_order"] == 2

    def test_cross_epic_dependencies(self) -> None:
        plan = {
            "epics": [
                {
                    "title": "Auth",
                    "stories": [{"title": "Login", "priority": 1, "dependencies": []}],
                },
                {
                    "title": "Dashboard",
                    "stories": [{"title": "Overview", "priority": 1, "dependencies": ["Login"]}],
                },
            ]
        }
        sorted_stories = topological_sort_stories(plan)
        titles = [s["title"] for s in sorted_stories]
        assert titles.index("Login") < titles.index("Overview")

    def test_tags_epic_title(self) -> None:
        plan = {
            "epics": [{
                "title": "Auth",
                "stories": [{"title": "Login", "priority": 1, "dependencies": []}],
            }]
        }
        sorted_stories = topological_sort_stories(plan)
        assert sorted_stories[0]["epic_title"] == "Auth"


# ─── validate_plan tests ───


class TestValidatePlan:
    @pytest.mark.asyncio
    async def test_no_epics(self) -> None:
        state = _make_state(plan={})
        result = await validate_plan(state)
        assert "No epics were generated" in result["validation_issues"]

    @pytest.mark.asyncio
    async def test_epic_without_stories(self) -> None:
        state = _make_state(
            plan={"epics": [{"title": "Auth", "stories": []}]},
        )
        result = await validate_plan(state)
        assert any("Auth" in i and "no user stories" in i for i in result["validation_issues"])

    @pytest.mark.asyncio
    async def test_invalid_dependency(self) -> None:
        state = _make_state(
            plan={
                "epics": [{
                    "title": "Auth",
                    "stories": [
                        {"title": "Login", "dependencies": ["NonExistent"]},
                    ],
                }]
            },
        )
        result = await validate_plan(state)
        assert any("NonExistent" in i for i in result["validation_issues"])

    @pytest.mark.asyncio
    async def test_valid_plan(self) -> None:
        state = _make_state(plan=SAMPLE_PLAN)
        result = await validate_plan(state)
        assert result["validation_issues"] == []


# ─── store_artifact tests ───


class TestStoreArtifact:
    @pytest.mark.asyncio
    async def test_no_session(self) -> None:
        state = _make_state(plan=SAMPLE_PLAN, _session=None)
        result = await store_artifact(state)
        assert any("No database session" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_no_plan(self) -> None:
        state = _make_state(plan={}, _session=AsyncMock())
        result = await store_artifact(state)
        assert any("No plan to store" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_stores_artifact(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        artifact_id = uuid.uuid4()

        async def mock_refresh(obj):
            obj.id = artifact_id

        session.refresh = AsyncMock(side_effect=mock_refresh)

        state = _make_state(plan=SAMPLE_PLAN, _session=session)
        result = await store_artifact(state)

        assert result["plan_artifact_id"] == str(artifact_id)
        session.add.assert_called_once()


# ─── import_plan_to_db tests ───


class TestImportPlanToDb:
    @pytest.mark.asyncio
    async def test_empty_plan(self) -> None:
        session = AsyncMock()
        result = await import_plan_to_db(session, uuid.uuid4(), None, {})
        assert result == {"epics_stored": 0, "stories_stored": 0}

    @pytest.mark.asyncio
    async def test_imports_epics_and_stories(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await import_plan_to_db(
            session, uuid.uuid4(), uuid.uuid4(), SAMPLE_PLAN
        )

        assert result["epics_stored"] == 2
        assert result["stories_stored"] == 3  # 2 in Auth + 1 in Dashboard
        # 2 epics + 3 stories = 5 add calls
        assert session.add.call_count == 5


# ─── Graph structure tests ───


class TestBuildDefineGraph:
    def test_graph_has_all_nodes(self) -> None:
        graph = build_plan_graph()
        node_names = set(graph.nodes.keys())
        expected = {
            "gather_context",
            "generate_plan",
            "validate_plan",
            "store_artifact",
        }
        assert expected.issubset(node_names)

    def test_entry_point_is_gather_context(self) -> None:
        graph = build_plan_graph()
        assert "gather_context" in graph.nodes
