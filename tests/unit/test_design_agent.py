"""Unit tests for the Design Agent (new Workflow → Task → Skill architecture)."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.design.agent import (
    DesignWorkflow,
    build_design_graph,
    create_initial_state,
    quality_gate,
)

PROJECT_ID = str(uuid.uuid4())
RUN_ID = str(uuid.uuid4())


# ─── LLM response fixtures ───

ANALYZE_REQS_RESPONSE = json.dumps({
    "system_purpose": "Inventory management system",
    "business_rules_by_domain": {
        "authentication": [{"title": "Lockout", "description": "Lock after 3 fails"}],
        "orders": [{"title": "Approval", "description": "Orders > $5K need approval"}],
    },
    "entities": [{"entity_name": "User"}, {"entity_name": "Order"}],
    "user_workflows": [{"journey_name": "Create Order", "steps": ["Login", "Submit"]}],
    "user_roles": [{"name": "admin"}, {"name": "manager"}],
    "non_functional_requirements": ["200 concurrent users"],
    "constraints": [],
    "security_requirements": ["SOC2"],
    "integration_points": [],
    "technology_assessment": "Legacy Flask app",
})

ARCH_RESPONSE = json.dumps({
    "pattern": "modular_monolith",
    "rationale": "Best fit",
    "trade_offs": ["Simple deployment"],
    "risks": [],
    "recommended_stack": [{"category": "backend", "technology": "FastAPI", "justification": "Async", "alternatives_considered": []}],
    "component_diagram": "",
    "communication_patterns": "",
    "deployment_model": "",
    "adrs": [],
})

SCHEMA_RESPONSE = json.dumps({
    "tables": [{"name": "users", "purpose": "Users", "columns": [], "primary_key": ["id"], "indexes": [], "constraints": []}],
    "ddl": "CREATE TABLE users (id UUID);",
    "indexes_ddl": "",
    "er_diagram_mermaid": "",
    "migrations": [],
    "design_notes": [],
})

API_RESPONSE = json.dumps({
    "base_path": "/api/v1",
    "endpoints": [{"method": "GET", "path": "/users", "summary": "List", "description": "", "tags": [], "auth_required": True, "required_roles": ["viewer"], "parameters": [], "request_schema": {}, "response_schema": {}, "error_responses": [], "rate_limit": "", "business_rules_enforced": []}],
    "openapi_yaml": "",
    "pagination_strategy": "cursor",
    "filtering_strategy": "query",
    "error_format": {},
    "rate_limiting": {},
})

AUTH_RESPONSE = json.dumps({
    "auth_strategy": "jwt",
    "oauth2_flows": [],
    "token_management": [{"type": "access", "expiry": "15m", "rotation_policy": "", "storage": "memory"}],
    "roles": [{"name": "admin", "description": "", "permissions": ["all"], "inherits_from": ""}],
    "permissions": [],
    "permission_matrix": {},
    "middleware_design": "",
    "security_measures": [],
    "password_policy": "",
    "session_management": "",
})

COMPONENT_RESPONSE = json.dumps({
    "framework": "Next.js",
    "routes": [{"path": "/dashboard", "page_component": "Dashboard", "layout": "Main", "auth_required": True, "required_roles": []}],
    "pages": [{"name": "Dashboard", "type": "page", "description": "", "props": [], "state": [], "api_calls": [], "children": [], "events": []}],
    "shared_components": [],
    "forms": [],
    "state_management": "React Query",
    "data_fetching": "",
    "component_tree_mermaid": "",
})

QUALITY_PASS = json.dumps({
    "scores": {"completeness": 85, "consistency": 80, "feasibility": 90, "traceability": 75, "security": 80},
    "overall_score": 82.75,
    "passing": True,
    "gaps": [],
    "suggestions": [],
})

QUALITY_FAIL = json.dumps({
    "scores": {"completeness": 40, "consistency": 50, "feasibility": 60, "traceability": 30, "security": 45},
    "overall_score": 45.0,
    "passing": False,
    "gaps": ["Missing CRUD"],
    "suggestions": ["Add endpoints"],
})


def _mock_llm_sequence(responses: list[str]) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=[AIMessage(content=r) for r in responses])
    return llm


def _mock_context_entries() -> list[MagicMock]:
    entries = []
    for cat, title, content in [
        ("business_rule", "Lockout", "Lock after 3 failed attempts"),
        ("business_rule", "Approval", "Orders over $5K need approval"),
        ("domain_entity", "User", '{"entity_name":"User"}'),
        ("domain_entity", "Order", '{"entity_name":"Order"}'),
        ("system_understanding", "System Understanding", '{"system_purpose":"Inventory system"}'),
    ]:
        entry = MagicMock()
        entry.category = cat
        entry.title = title
        entry.content = content
        entry.metadata_ = {}
        entries.append(entry)
    return entries


# ─── quality_gate routing tests ───


def test_quality_gate_pass() -> None:
    state = create_initial_state(project_id=PROJECT_ID)
    state["quality_score"] = 85.0
    state["quality_retries"] = 0
    assert quality_gate(state) == "pass"


def test_quality_gate_retry() -> None:
    state = create_initial_state(project_id=PROJECT_ID)
    state["quality_score"] = 50.0
    state["quality_retries"] = 0
    assert quality_gate(state) == "retry"


def test_quality_gate_max_retries() -> None:
    state = create_initial_state(project_id=PROJECT_ID)
    state["quality_score"] = 50.0
    state["quality_retries"] = 2
    assert quality_gate(state) == "max_retries_reached"


# ─── State creation tests ───


def test_create_initial_state_defaults() -> None:
    state = create_initial_state(project_id=PROJECT_ID, agent_run_id=RUN_ID)
    assert state["project_id"] == PROJECT_ID
    assert state["agent_run_id"] == RUN_ID
    assert state["task_outputs"] == {}
    assert state["quality_score"] == 0.0
    assert state["quality_retries"] == 0
    assert state["errors"] == []


def test_create_initial_state_with_reviewer_notes() -> None:
    state = create_initial_state(project_id=PROJECT_ID, reviewer_notes="Fix auth section")
    assert state["reviewer_notes"] == "Fix auth section"


def test_create_initial_state_with_deps() -> None:
    llm = MagicMock()
    repo = MagicMock()
    session = MagicMock()
    state = create_initial_state(project_id=PROJECT_ID, llm=llm, repository=repo, session=session)
    assert state["_llm"] is llm
    assert state["_repository"] is repo
    assert state["_session"] is session


# ─── Graph structure tests ───


def test_build_design_graph_compiles() -> None:
    graph = build_design_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_workflow_builds_graph() -> None:
    workflow = DesignWorkflow()
    compiled = workflow.compile()
    assert compiled is not None


def test_workflow_metadata() -> None:
    workflow = DesignWorkflow()
    assert workflow.name == "design"
    assert workflow.quality_threshold == 70.0


# ─── Full workflow integration test ───


@pytest.mark.asyncio
async def test_full_workflow_passing() -> None:
    """Full pipeline: load → analyze → arch → schema → api → auth → frontend → quality(pass) → store."""
    # 8 LLM calls: analyze_reqs, arch_skill, schema_skill, api_skill, auth_skill, component_skill, quality
    llm = _mock_llm_sequence([
        ANALYZE_REQS_RESPONSE,
        ARCH_RESPONSE,
        SCHEMA_RESPONSE,
        API_RESPONSE,
        AUTH_RESPONSE,
        COMPONENT_RESPONSE,
        QUALITY_PASS,
    ])

    repo = AsyncMock()
    repo.get_all_for_project.return_value = _mock_context_entries()

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    initial = create_initial_state(
        project_id=PROJECT_ID,
        agent_run_id=RUN_ID,
        llm=llm,
        repository=repo,
        session=session,
    )

    workflow = DesignWorkflow()
    compiled = workflow.compile()
    result = await compiled.ainvoke(initial)

    assert result.get("quality_score", 0) >= 70
    assert result.get("artifacts_stored", 0) >= 1
    assert session.add.call_count >= 1


@pytest.mark.asyncio
async def test_full_workflow_with_retry() -> None:
    """Quality fails on first pass, retries, then passes."""
    llm = _mock_llm_sequence([
        # First pass
        ANALYZE_REQS_RESPONSE,
        ARCH_RESPONSE,
        SCHEMA_RESPONSE,
        API_RESPONSE,
        AUTH_RESPONSE,
        COMPONENT_RESPONSE,
        QUALITY_FAIL,
        # Retry (starts from generate_architecture)
        ARCH_RESPONSE,
        SCHEMA_RESPONSE,
        API_RESPONSE,
        AUTH_RESPONSE,
        COMPONENT_RESPONSE,
        QUALITY_PASS,
    ])

    repo = AsyncMock()
    repo.get_all_for_project.return_value = _mock_context_entries()

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    initial = create_initial_state(
        project_id=PROJECT_ID,
        agent_run_id=RUN_ID,
        llm=llm,
        repository=repo,
        session=session,
    )

    workflow = DesignWorkflow()
    compiled = workflow.compile()
    result = await compiled.ainvoke(initial)

    assert result.get("quality_retries", 0) >= 1
    assert result.get("quality_score", 0) >= 70


@pytest.mark.asyncio
async def test_workflow_no_repo_continues_with_empty_context() -> None:
    """Workflow proceeds with empty context when no repo is provided."""
    llm = _mock_llm_sequence([
        ANALYZE_REQS_RESPONSE,  # Won't be called (no context)
        QUALITY_PASS,
    ])

    initial = create_initial_state(project_id=PROJECT_ID, llm=llm)

    workflow = DesignWorkflow()
    compiled = workflow.compile()
    result = await compiled.ainvoke(initial)

    assert any("No repository" in e for e in result.get("errors", []))
