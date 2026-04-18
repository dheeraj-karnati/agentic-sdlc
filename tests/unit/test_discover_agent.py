"""Unit tests for the Discovery Agent (new architecture).

These tests verify the workflow routing functions and the backward-compatible
build_discover_graph() function.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.discover.agent import (
    DiscoverWorkflow,
    build_discover_graph,
    clarification_check,
    create_initial_state,
    quality_gate,
)


SAMPLE_DOCUMENT = """\
Legacy Order Management System - Technical Specification

1. Business Rules:
- Orders over $10,000 require manager approval before processing.
- Customers with credit score below 600 must pay upfront.
- Returns are accepted within 30 days of purchase with original receipt.

2. Requirements:
- The system must support 500 concurrent users.
- All transactions must be logged for SOX compliance.
- Integration with SAP ERP for inventory sync every 15 minutes.

3. Technical Details:
- Built on Oracle 11g with PL/SQL stored procedures.
- REST API exposed via Apache Tomcat 8.5.
- Authentication uses LDAP against corporate Active Directory.
"""


def _mock_llm_response(content: str) -> MagicMock:
    """Create a mock LLM that returns the given content."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return llm


# ─── Routing function tests ───


def test_quality_gate_passes_at_threshold() -> None:
    """quality_gate returns 'pass' when score >= 70."""
    state = create_initial_state(project_id="test-id", document_text="")
    state["quality_score"] = 70.0
    state["quality_retries"] = 0
    assert quality_gate(state) == "pass"


def test_quality_gate_retries_below_threshold() -> None:
    """quality_gate returns 'retry' when score < 70 and retries available."""
    state = create_initial_state(project_id="test-id", document_text="")
    state["quality_score"] = 50.0
    state["quality_retries"] = 1
    assert quality_gate(state) == "retry"


def test_quality_gate_max_retries_reached() -> None:
    """quality_gate returns 'max_retries_reached' after 2 retries."""
    state = create_initial_state(project_id="test-id", document_text="")
    state["quality_score"] = 50.0
    state["quality_retries"] = 2
    assert quality_gate(state) == "max_retries_reached"


def test_clarification_check_with_questions() -> None:
    """clarification_check routes to 'has_questions' when questions exist."""
    state = create_initial_state(project_id="test-id", document_text="")
    state["pending_questions"] = [{"question": "What is X?"}]
    assert clarification_check(state) == "has_questions"


def test_clarification_check_clear() -> None:
    """clarification_check routes to 'clear' when no questions."""
    state = create_initial_state(project_id="test-id", document_text="")
    state["pending_questions"] = []
    assert clarification_check(state) == "clear"


def test_clarification_check_skip_overrides_questions() -> None:
    """skip_clarity=True forces 'clear' even with pending questions."""
    state = create_initial_state(project_id="test-id", document_text="")
    state["skip_clarity"] = True
    state["pending_questions"] = [{"question": "What is X?"}]
    assert clarification_check(state) == "clear"


# ─── State creation tests ───


def test_create_initial_state_defaults() -> None:
    """create_initial_state produces correct defaults."""
    state = create_initial_state(
        project_id="00000000-0000-0000-0000-000000000001",
        document_text="some text",
    )
    assert state["project_id"] == "00000000-0000-0000-0000-000000000001"
    assert state["document_text"] == "some text"
    assert state["task_outputs"] == {}
    assert state["pending_questions"] == []
    assert state["quality_score"] == 0.0
    assert state["quality_retries"] == 0
    assert state["errors"] == []


def test_create_initial_state_with_files() -> None:
    """create_initial_state accepts files parameter."""
    files = [{"filename": "app.py", "content": "print('hello')"}]
    state = create_initial_state(
        project_id="test-id",
        files=files,
    )
    assert state["files"] == files


def test_create_initial_state_with_injected_deps() -> None:
    """create_initial_state stores injected dependencies."""
    llm = MagicMock()
    repo = MagicMock()
    embed_fn = AsyncMock()

    state = create_initial_state(
        project_id="test-id",
        llm=llm,
        repository=repo,
        embed_fn=embed_fn,
    )
    assert state["_llm"] is llm
    assert state["_repository"] is repo
    assert state["_embed_fn"] is embed_fn


# ─── Graph structure tests ───


def test_build_discover_graph_compiles() -> None:
    """build_discover_graph produces a compilable graph."""
    graph = build_discover_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_workflow_class_builds_graph() -> None:
    """DiscoverWorkflow.build_graph() produces a compilable graph."""
    workflow = DiscoverWorkflow()
    graph = workflow.build_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_workflow_compile_shortcut() -> None:
    """DiscoverWorkflow.compile() produces a runnable graph."""
    workflow = DiscoverWorkflow()
    compiled = workflow.compile()
    assert compiled is not None


def test_workflow_metadata() -> None:
    """DiscoverWorkflow has correct name and description."""
    workflow = DiscoverWorkflow()
    assert workflow.name == "discover"
    assert "legacy" in workflow.description.lower() or "analyze" in workflow.description.lower()
    assert workflow.quality_threshold == 70.0
    assert workflow.max_quality_retries == 2
