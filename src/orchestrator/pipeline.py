"""
D8X orchestrator: LangGraph state machine for the SDLC agent pipeline.

Pipeline: D1:Ingest → D2:Discover → D3:Design → D4:Prototype →
D5:Plan → D6:Build → D7:Test → D8:Ship

Feedback loops:
  - Test failed → route back to Build with failure report
  - Ship errors → route back to Build with error analysis
"""

from __future__ import annotations

from datetime import datetime, timezone

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


# ─── Shared Workflow State ───


class WorkflowState(TypedDict):
    """State that persists across all agents in the D8X pipeline."""

    project_id: str
    project_name: str
    current_phase: str  # ingest|discover|design|prototype|plan|build|test|ship
    phase_status: str  # running|paused_for_input|paused_for_approval|completed|failed
    pending_questions: list[dict]
    user_responses: list[dict]
    approval_decision: str | None  # approved|rejected|revision_requested
    phase_outputs: dict[str, dict]
    test_result: str  # pass|fail (from Test agent)
    test_report: dict  # QA failure details for Build context
    errors: list[str]
    started_at: str
    updated_at: str


def create_initial_state(project_id: str, project_name: str) -> WorkflowState:
    """Create a fresh workflow state for a new project."""
    now = datetime.now(timezone.utc).isoformat()
    return WorkflowState(
        project_id=project_id,
        project_name=project_name,
        current_phase="ingest",
        phase_status="pending",
        pending_questions=[],
        user_responses=[],
        approval_decision=None,
        phase_outputs={},
        test_result="",
        test_report={},
        errors=[],
        started_at=now,
        updated_at=now,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Phase Nodes (stubs — replaced by actual agent subgraphs) ───


async def ingest_node(state: WorkflowState) -> WorkflowState:
    """D1: Ingest — parse any input format into structured text."""
    state["current_phase"] = "ingest"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def discover_node(state: WorkflowState) -> WorkflowState:
    """D2: Discover — extract requirements, rules, entities, conflicts."""
    state["current_phase"] = "discover"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def design_node(state: WorkflowState) -> WorkflowState:
    """D3: Design — architecture, DB schema, API contracts, auth."""
    state["current_phase"] = "design"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def prototype_node(state: WorkflowState) -> WorkflowState:
    """D4: Prototype — interactive demo with stakeholder feedback."""
    state["current_phase"] = "prototype"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def plan_node(state: WorkflowState) -> WorkflowState:
    """D5: Plan — epics, sequenced user stories, detailed ACs."""
    state["current_phase"] = "plan"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def build_node(state: WorkflowState) -> WorkflowState:
    """D6: Build — story-by-story code generation, GitHub PRs."""
    state["current_phase"] = "build"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def test_node(state: WorkflowState) -> WorkflowState:
    """D7: Test — QA, security scans, accessibility, coverage."""
    state["current_phase"] = "test"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def ship_node(state: WorkflowState) -> WorkflowState:
    """D8: Ship — deploy, monitor logs, error feedback to Build."""
    state["current_phase"] = "ship"
    state["phase_status"] = "running"
    state["updated_at"] = _now()
    return state


async def approval_gate(state: WorkflowState) -> WorkflowState:
    """Pauses the workflow for human review and approval."""
    state["phase_status"] = "paused_for_approval"
    state["approval_decision"] = None
    state["updated_at"] = _now()
    return state


def should_continue(state: WorkflowState) -> str:
    """Route based on approval decision."""
    decision = state.get("approval_decision")
    if decision == "approved":
        return "next_phase"
    elif decision == "revision_requested":
        return "retry_phase"
    elif decision == "rejected":
        return "end"
    return "wait"


def test_router(state: WorkflowState) -> str:
    """Route after Test: pass → Ship approval, fail → back to Build."""
    if state.get("test_result") == "fail":
        return "feedback_to_build"
    return "next_phase"


def ship_router(state: WorkflowState) -> str:
    """Route after Ship: success → approval, error → back to Build."""
    if state.get("phase_status") == "failed":
        return "feedback_to_build"
    return "next_phase"


# ─── Build the D8X Pipeline ───


def build_pipeline() -> StateGraph:
    """Build the LangGraph pipeline for the D8X flow.

    D1:Ingest → D2:Discover → D3:Design → D4:Prototype →
    D5:Plan → D6:Build → D7:Test → D8:Ship

    Feedback loops: Test→Build on QA failure, Ship→Build on deploy error.
    """
    graph = StateGraph(WorkflowState)

    # Phase nodes
    for name, fn in [
        ("ingest", ingest_node), ("discover", discover_node),
        ("design", design_node), ("prototype", prototype_node),
        ("plan", plan_node), ("build", build_node),
        ("test", test_node), ("ship", ship_node),
    ]:
        graph.add_node(name, fn)

    # Approval gates
    for name in ["ingest", "discover", "design", "prototype", "plan", "build", "test", "ship"]:
        graph.add_node(f"approval_{name}", approval_gate)

    # Entry point
    graph.set_entry_point("ingest")

    # Phase → Approval edges (linear pipeline)
    for name in ["ingest", "discover", "design", "prototype", "plan", "build"]:
        graph.add_edge(name, f"approval_{name}")

    # Ship goes to its approval gate via router
    graph.add_conditional_edges("ship", ship_router, {
        "next_phase": "approval_ship",
        "feedback_to_build": "build",
    })

    # Test has special routing (feedback loop to Build on failure)
    graph.add_conditional_edges("test", test_router, {
        "next_phase": "approval_test",
        "feedback_to_build": "build",
    })

    # Approval → Next phase routing
    transitions = [
        ("approval_ingest", "discover", "ingest"),
        ("approval_discover", "design", "discover"),
        ("approval_design", "prototype", "design"),
        ("approval_prototype", "plan", "prototype"),
        ("approval_plan", "build", "plan"),
        ("approval_build", "test", "build"),
        ("approval_test", "ship", "test"),
        ("approval_ship", END, "ship"),
    ]
    for approval, next_node, retry_node in transitions:
        graph.add_conditional_edges(approval, should_continue, {
            "next_phase": next_node,
            "retry_phase": retry_node,
            "end": END,
            "wait": END,
        })

    return graph
