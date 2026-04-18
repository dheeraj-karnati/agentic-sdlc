"""Smoke tests for the D8X pipeline — verifies all 8 agents compile and connect."""

import pytest

from src.orchestrator.pipeline import WorkflowState, build_pipeline, create_initial_state


def test_pipeline_compiles() -> None:
    """The full D8X pipeline graph should compile without errors."""
    graph = build_pipeline()
    compiled = graph.compile()
    assert compiled is not None


def test_pipeline_initial_state() -> None:
    state = create_initial_state(project_id="test-id", project_name="Test")
    assert state["current_phase"] == "ingest"
    assert state["phase_status"] == "pending"
    assert state["test_result"] == ""


def test_all_agent_workflows_compile() -> None:
    """Each individual agent workflow should compile independently."""
    from src.agents.ingest.agent import IngestWorkflow
    from src.agents.discover.agent import DiscoverWorkflow
    from src.agents.design.agent import DesignWorkflow
    from src.agents.test.agent import TestWorkflow
    from src.agents.build.agent import BuildWorkflow
    from src.agents.ship.agent import ShipWorkflow

    for wf_class in [IngestWorkflow, DiscoverWorkflow, DesignWorkflow, TestWorkflow, BuildWorkflow, ShipWorkflow]:
        wf = wf_class()
        compiled = wf.compile()
        assert compiled is not None, f"{wf_class.__name__} failed to compile"


def test_pipeline_has_all_d8_nodes() -> None:
    """Pipeline should have nodes for all 8 agents plus their approval gates."""
    graph = build_pipeline()
    node_names = set(graph.nodes.keys())

    for agent in ["ingest", "discover", "design", "prototype", "plan", "build", "test", "ship"]:
        assert agent in node_names, f"Missing agent node: {agent}"
        assert f"approval_{agent}" in node_names, f"Missing approval gate: approval_{agent}"


def test_phase_transitions_cover_all_agents() -> None:
    """Approval system should have transitions for all 8 agent types."""
    from src.orchestrator.approval import PHASE_TRANSITIONS, PHASE_STATUS
    from src.context_store.models import AgentType

    for agent_type in AgentType:
        assert agent_type in PHASE_TRANSITIONS, f"Missing transition for {agent_type}"
        assert agent_type in PHASE_STATUS, f"Missing status for {agent_type}"


def test_agent_type_enum_has_all_d8() -> None:
    """AgentType enum should have all 8 agents."""
    from src.context_store.models import AgentType

    expected = {"ingest", "discover", "design", "prototype", "plan", "build", "test", "ship"}
    actual = {a.value for a in AgentType}
    assert expected == actual


def test_project_status_enum_has_all_phases() -> None:
    """ProjectStatus enum should have all phases."""
    from src.context_store.models import ProjectStatus

    expected = {"created", "ingest", "discover", "design", "prototype", "plan", "build", "test", "ship", "completed"}
    actual = {s.value for s in ProjectStatus}
    assert expected == actual
