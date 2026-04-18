"""Unit tests for Design Agent tasks (mock LLM calls)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.design.tasks.analyze_requirements_task import (
    AnalyzeRequirementsInput,
    AnalyzeRequirementsTask,
    StructuredRequirements,
)
from src.agents.design.tasks.design_quality_assessment_task import (
    DesignQualityAssessment,
    DesignQualityAssessmentTask,
    DesignQualityInput,
    DesignQualityScores,
)
from src.agents.design.tasks.generate_architecture_task import (
    GenerateArchitectureInput,
    GenerateArchitectureTask,
)
from src.agents.design.tasks.generate_data_model_task import (
    GenerateDataModelInput,
    GenerateDataModelTask,
)
from src.agents.design.tasks.generate_api_contracts_task import (
    GenerateAPIContractsInput,
    GenerateAPIContractsTask,
)
from src.agents.design.tasks.generate_auth_model_task import (
    GenerateAuthModelInput,
    GenerateAuthModelTask,
)
from src.agents.design.tasks.generate_frontend_design_task import (
    GenerateFrontendDesignInput,
    GenerateFrontendDesignTask,
)


def _mock_llm(content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return llm


SAMPLE_REQS = {
    "system_purpose": "Inventory management system",
    "business_rules_by_domain": {
        "authentication": [{"title": "Lockout", "description": "Lock after 3 failed attempts"}],
        "orders": [{"title": "Approval", "description": "Orders over $5K need approval"}],
    },
    "entities": [
        {"entity_name": "User", "attributes": [{"name": "email"}]},
        {"entity_name": "Order", "attributes": [{"name": "total"}]},
    ],
    "user_workflows": [{"journey_name": "Create Order", "steps": ["Login", "Add items", "Submit"]}],
    "user_roles": [{"name": "admin"}, {"name": "manager"}, {"name": "viewer"}],
    "non_functional_requirements": ["200 concurrent users", "500ms response time"],
    "constraints": ["Budget: $450K"],
    "security_requirements": ["SOC2 compliance", "Encryption at rest"],
    "integration_points": [],
    "technology_assessment": "Legacy Flask app with PostgreSQL",
}


# ─── AnalyzeRequirementsTask ───


@pytest.mark.asyncio
async def test_analyze_requirements_structures_context() -> None:
    response = json.dumps(SAMPLE_REQS)
    llm = _mock_llm(response)
    task = AnalyzeRequirementsTask()

    result = await task.execute(
        AnalyzeRequirementsInput(business_context=[
            {"category": "business_rule", "title": "Lockout", "content": "Lock after 3 fails", "metadata": {}},
            {"category": "domain_entity", "title": "Order", "content": "Purchase order", "metadata": {}},
        ]),
        llm=llm,
    )
    assert isinstance(result, StructuredRequirements)
    assert result.business_rules_by_domain
    assert len(result.entities) >= 1


@pytest.mark.asyncio
async def test_analyze_requirements_validation() -> None:
    task = AnalyzeRequirementsTask()
    empty = StructuredRequirements()
    assert task.validate(empty) is False

    with_data = StructuredRequirements(entities=[{"entity_name": "User"}])
    assert task.validate(with_data) is True


# ─── GenerateArchitectureTask ───


ARCH_SKILL_RESPONSE = json.dumps({
    "pattern": "modular_monolith",
    "rationale": "Best fit for team size and complexity",
    "trade_offs": ["Simpler deployment"],
    "risks": [{"risk": "Coupling", "likelihood": "medium", "impact": "medium", "mitigation": "Module boundaries"}],
    "recommended_stack": [{"category": "backend", "technology": "FastAPI", "justification": "Async", "alternatives_considered": []}],
    "component_diagram": "",
    "communication_patterns": "Internal calls",
    "deployment_model": "Docker",
    "adrs": [{"title": "ADR-001", "context": "context", "decision": "decision", "consequences": "consequences"}],
})


@pytest.mark.asyncio
async def test_generate_architecture_returns_output() -> None:
    llm = _mock_llm(ARCH_SKILL_RESPONSE)
    task = GenerateArchitectureTask(llm=llm)
    result = await task.execute(
        GenerateArchitectureInput(structured_requirements=SAMPLE_REQS), llm=llm,
    )
    assert result.architecture
    assert result.architecture["pattern"] == "modular_monolith"


# ─── GenerateDataModelTask ───


SCHEMA_SKILL_RESPONSE = json.dumps({
    "tables": [{"name": "users", "purpose": "Users", "columns": [], "primary_key": ["id"], "indexes": [], "constraints": []}],
    "ddl": "CREATE TABLE users (id UUID PRIMARY KEY);",
    "indexes_ddl": "",
    "er_diagram_mermaid": "erDiagram",
    "migrations": [{"version": "001", "description": "Init", "up_sql": "CREATE TABLE users...", "down_sql": "DROP TABLE users;"}],
    "design_notes": ["UUID primary keys"],
})


@pytest.mark.asyncio
async def test_generate_data_model_returns_schema() -> None:
    llm = _mock_llm(SCHEMA_SKILL_RESPONSE)
    task = GenerateDataModelTask(llm=llm)
    result = await task.execute(
        GenerateDataModelInput(structured_requirements=SAMPLE_REQS), llm=llm,
    )
    assert result.database_schema
    assert "tables" in result.database_schema


# ─── GenerateAPIContractsTask ───


API_SKILL_RESPONSE = json.dumps({
    "base_path": "/api/v1",
    "endpoints": [{"method": "GET", "path": "/products", "summary": "List", "description": "", "tags": [], "auth_required": True, "required_roles": ["viewer"], "parameters": [], "request_schema": {}, "response_schema": {}, "error_responses": [], "rate_limit": "", "business_rules_enforced": []}],
    "openapi_yaml": "openapi: 3.1.0",
    "pagination_strategy": "cursor",
    "filtering_strategy": "query params",
    "error_format": {},
    "rate_limiting": {},
})


@pytest.mark.asyncio
async def test_generate_api_contracts_returns_spec() -> None:
    llm = _mock_llm(API_SKILL_RESPONSE)
    task = GenerateAPIContractsTask(llm=llm)
    result = await task.execute(
        GenerateAPIContractsInput(structured_requirements=SAMPLE_REQS), llm=llm,
    )
    assert result.api_specification
    assert "endpoints" in result.api_specification


# ─── GenerateAuthModelTask ───


AUTH_SKILL_RESPONSE = json.dumps({
    "auth_strategy": "jwt",
    "oauth2_flows": [],
    "token_management": [{"type": "access", "expiry": "15m", "rotation_policy": "", "storage": "memory"}],
    "roles": [{"name": "admin", "description": "Full access", "permissions": ["all"], "inherits_from": ""}],
    "permissions": [],
    "permission_matrix": {"admin": ["all"]},
    "middleware_design": "JWT middleware",
    "security_measures": [{"measure": "bcrypt", "description": "Password hashing", "configuration": "cost 12"}],
    "password_policy": "12 chars min",
    "session_management": "Stateless JWT",
})


@pytest.mark.asyncio
async def test_generate_auth_model_returns_design() -> None:
    llm = _mock_llm(AUTH_SKILL_RESPONSE)
    task = GenerateAuthModelTask(llm=llm)
    result = await task.execute(
        GenerateAuthModelInput(structured_requirements=SAMPLE_REQS), llm=llm,
    )
    assert result.auth_design
    assert result.auth_design["auth_strategy"] == "jwt"


@pytest.mark.asyncio
async def test_generate_auth_model_extracts_auth_rules() -> None:
    """Auth task should include rules from auth domain AND role-related rules from other domains."""
    llm = _mock_llm(AUTH_SKILL_RESPONSE)
    task = GenerateAuthModelTask(llm=llm)
    reqs = dict(SAMPLE_REQS)
    reqs["business_rules_by_domain"] = {
        "authentication": [{"title": "Lockout", "description": "Lock after 3 fails"}],
        "orders": [{"title": "Admin approval", "description": "Admin role required for approval"}],
        "inventory": [{"title": "Stock check", "description": "Check stock levels"}],
    }
    result = await task.execute(GenerateAuthModelInput(structured_requirements=reqs), llm=llm)
    assert result.auth_design


# ─── GenerateFrontendDesignTask ───


COMPONENT_SKILL_RESPONSE = json.dumps({
    "framework": "Next.js 14",
    "routes": [{"path": "/dashboard", "page_component": "Dashboard", "layout": "Main", "auth_required": True, "required_roles": ["viewer"]}],
    "pages": [{"name": "Dashboard", "type": "page", "description": "Main view", "props": [], "state": [], "api_calls": [], "children": [], "events": []}],
    "shared_components": [],
    "forms": [],
    "state_management": "React Query + Zustand",
    "data_fetching": "React Query",
    "component_tree_mermaid": "",
})


@pytest.mark.asyncio
async def test_generate_frontend_design_returns_components() -> None:
    llm = _mock_llm(COMPONENT_SKILL_RESPONSE)
    task = GenerateFrontendDesignTask(llm=llm)
    result = await task.execute(
        GenerateFrontendDesignInput(
            structured_requirements=SAMPLE_REQS,
            api_specification={"endpoints": [{"method": "GET", "path": "/products"}]},
        ),
        llm=llm,
    )
    assert result.frontend_components
    assert result.frontend_components["framework"] == "Next.js 14"


# ─── DesignQualityAssessmentTask ───


QUALITY_PASS_RESPONSE = json.dumps({
    "scores": {"completeness": 85, "consistency": 80, "feasibility": 90, "traceability": 75, "security": 80},
    "overall_score": 82.75,
    "passing": True,
    "gaps": [],
    "suggestions": [],
})

QUALITY_FAIL_RESPONSE = json.dumps({
    "scores": {"completeness": 40, "consistency": 50, "feasibility": 70, "traceability": 30, "security": 45},
    "overall_score": 46.75,
    "passing": False,
    "gaps": ["No CRUD for Order entity", "Auth roles inconsistent"],
    "suggestions": ["Add full CRUD for all entities", "Align auth roles across all layers"],
})


@pytest.mark.asyncio
async def test_quality_assessment_passing() -> None:
    llm = _mock_llm(QUALITY_PASS_RESPONSE)
    task = DesignQualityAssessmentTask()
    result = await task.execute(
        DesignQualityInput(
            architecture={"pattern": "modular_monolith"},
            database_schema={"tables": [{"name": "users"}]},
            api_specification={"endpoints": [{"path": "/users"}]},
            auth_design={"roles": [{"name": "admin"}]},
            frontend_components={"pages": [{"name": "Dashboard"}]},
            structured_requirements=SAMPLE_REQS,
        ),
        llm=llm,
    )
    assert isinstance(result, DesignQualityAssessment)
    assert result.overall_score >= 70
    assert result.passing is True


@pytest.mark.asyncio
async def test_quality_assessment_failing() -> None:
    llm = _mock_llm(QUALITY_FAIL_RESPONSE)
    task = DesignQualityAssessmentTask()
    result = await task.execute(DesignQualityInput(), llm=llm)
    assert result.overall_score < 70
    assert result.passing is False
    assert len(result.gaps) >= 1


@pytest.mark.asyncio
async def test_quality_validation_rejects_bad_scores() -> None:
    task = DesignQualityAssessmentTask()
    bad = DesignQualityAssessment(scores=DesignQualityScores(completeness=150), overall_score=80)
    assert task.validate(bad) is False

    negative = DesignQualityAssessment(scores=DesignQualityScores(security=-5), overall_score=50)
    assert task.validate(negative) is False
