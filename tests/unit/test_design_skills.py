"""Unit tests for Design Agent skills (mock LLM calls)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.design.skills.api_contract_skill import (
    APIContractInput,
    APIContractSkill,
    APISpecification,
)
from src.agents.design.skills.architecture_decision_skill import (
    ArchitectureDecisionInput,
    ArchitectureDecisionSkill,
    ArchitectureDecision,
)
from src.agents.design.skills.auth_design_skill import (
    AuthDesignInput,
    AuthDesignSkill,
    AuthDesign,
)
from src.agents.design.skills.component_design_skill import (
    ComponentDesignInput,
    ComponentDesignSkill,
    ComponentArchitecture,
)
from src.agents.design.skills.schema_design_skill import (
    DatabaseSchema,
    SchemaDesignInput,
    SchemaDesignSkill,
)


def _mock_llm(content: str) -> MagicMock:
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return llm


# ─── ArchitectureDecisionSkill ───


ARCH_RESPONSE = json.dumps({
    "pattern": "modular_monolith",
    "rationale": "A modular monolith provides the right balance between simplicity and scalability for this team size and complexity.",
    "trade_offs": ["Less scalability than microservices", "Simpler deployment"],
    "risks": [{"risk": "Module coupling", "likelihood": "medium", "impact": "medium", "mitigation": "Enforce module boundaries"}],
    "recommended_stack": [
        {"category": "backend_framework", "technology": "FastAPI", "justification": "Async support", "alternatives_considered": ["Django", "Flask"]},
        {"category": "database", "technology": "PostgreSQL 16", "justification": "pgvector support", "alternatives_considered": ["MySQL"]},
    ],
    "component_diagram": "graph TD; A[API] --> B[Auth]; A --> C[Inventory]",
    "communication_patterns": "Internal function calls between modules",
    "deployment_model": "Single container with Docker Compose",
    "adrs": [{"title": "ADR-001: Use modular monolith", "context": "Small team", "decision": "Monolith with modules", "consequences": "Simpler ops"}],
})


@pytest.mark.asyncio
async def test_architecture_decision_produces_output() -> None:
    llm = _mock_llm(ARCH_RESPONSE)
    skill = ArchitectureDecisionSkill(llm=llm)
    result = await skill.run(ArchitectureDecisionInput(
        system_understanding="Inventory management system",
        business_rules=[{"rule_name": "order_approval"}],
        entity_list=[{"entity_name": "Order"}],
    ))
    assert isinstance(result, ArchitectureDecision)
    assert result.pattern == "modular_monolith"
    assert len(result.recommended_stack) >= 2
    assert len(result.adrs) >= 1


@pytest.mark.asyncio
async def test_architecture_decision_has_trade_offs() -> None:
    llm = _mock_llm(ARCH_RESPONSE)
    skill = ArchitectureDecisionSkill(llm=llm)
    result = await skill.run(ArchitectureDecisionInput(system_understanding="test"))
    assert len(result.trade_offs) >= 1
    assert len(result.risks) >= 1


# ─── SchemaDesignSkill ───


SCHEMA_RESPONSE = json.dumps({
    "tables": [
        {
            "name": "users",
            "purpose": "User accounts",
            "columns": [
                {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY DEFAULT gen_random_uuid()", "description": "Primary key"},
                {"name": "email", "type": "VARCHAR(255)", "constraints": "NOT NULL UNIQUE", "description": "User email"},
                {"name": "created_at", "type": "TIMESTAMPTZ", "constraints": "NOT NULL DEFAULT NOW()", "description": "Creation timestamp"},
            ],
            "primary_key": ["id"],
            "indexes": [{"name": "idx_users_email", "columns": ["email"], "unique": True, "purpose": "Email lookup"}],
            "constraints": [],
        },
        {
            "name": "orders",
            "purpose": "Purchase orders",
            "columns": [
                {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY", "description": "PK"},
                {"name": "user_id", "type": "UUID", "constraints": "NOT NULL REFERENCES users(id)", "description": "FK to users"},
                {"name": "total", "type": "DECIMAL(12,2)", "constraints": "NOT NULL CHECK (total >= 0)", "description": "Order total"},
            ],
            "primary_key": ["id"],
            "indexes": [{"name": "idx_orders_user_id", "columns": ["user_id"], "unique": False, "purpose": "FK lookup"}],
            "constraints": [],
        },
    ],
    "ddl": "CREATE TABLE users (id UUID PRIMARY KEY);\\nCREATE TABLE orders (id UUID PRIMARY KEY);",
    "indexes_ddl": "CREATE INDEX idx_orders_user_id ON orders(user_id);",
    "er_diagram_mermaid": "erDiagram\\n    USERS ||--o{ ORDERS : places",
    "migrations": [{"version": "001", "description": "Initial schema", "up_sql": "CREATE TABLE users...", "down_sql": "DROP TABLE users;"}],
    "design_notes": ["All tables use UUID primary keys", "Audit columns on all tables"],
})


@pytest.mark.asyncio
async def test_schema_design_produces_tables() -> None:
    llm = _mock_llm(SCHEMA_RESPONSE)
    skill = SchemaDesignSkill(llm=llm)
    result = await skill.run(SchemaDesignInput(
        entities=[{"entity_name": "User"}, {"entity_name": "Order"}],
        business_rules=[{"rule_name": "order_total_positive"}],
    ))
    assert isinstance(result, DatabaseSchema)
    assert len(result.tables) >= 2
    table_names = [t.name for t in result.tables]
    assert "users" in table_names
    assert "orders" in table_names


@pytest.mark.asyncio
async def test_schema_design_has_ddl() -> None:
    llm = _mock_llm(SCHEMA_RESPONSE)
    skill = SchemaDesignSkill(llm=llm)
    result = await skill.run(SchemaDesignInput(entities=[{"entity_name": "User"}]))
    assert result.ddl
    assert result.er_diagram_mermaid


@pytest.mark.asyncio
async def test_schema_design_has_migrations() -> None:
    llm = _mock_llm(SCHEMA_RESPONSE)
    skill = SchemaDesignSkill(llm=llm)
    result = await skill.run(SchemaDesignInput(entities=[{"entity_name": "User"}]))
    assert len(result.migrations) >= 1
    assert result.migrations[0].up_sql


# ─── APIContractSkill ───


API_RESPONSE = json.dumps({
    "base_path": "/api/v1",
    "endpoints": [
        {
            "method": "GET",
            "path": "/api/v1/products",
            "summary": "List products",
            "description": "Returns paginated product list",
            "tags": ["products"],
            "auth_required": True,
            "required_roles": ["viewer", "manager", "admin"],
            "parameters": [{"name": "page", "location": "query", "type": "integer", "required": False, "description": "Page number"}],
            "request_schema": {},
            "response_schema": {"items": "array", "total": "integer"},
            "error_responses": [{"status": 401, "description": "Unauthorized"}],
            "rate_limit": "100/min",
            "business_rules_enforced": [],
        },
        {
            "method": "POST",
            "path": "/api/v1/orders",
            "summary": "Create order",
            "description": "Create a new purchase order",
            "tags": ["orders"],
            "auth_required": True,
            "required_roles": ["manager", "admin"],
            "parameters": [],
            "request_schema": {"items": "array"},
            "response_schema": {"id": "string", "status": "string"},
            "error_responses": [{"status": 400, "description": "Validation error"}],
            "rate_limit": "30/min",
            "business_rules_enforced": ["order_approval_threshold"],
        },
    ],
    "openapi_yaml": "openapi: 3.1.0\\ninfo:\\n  title: API",
    "pagination_strategy": "Cursor-based pagination with page and limit params",
    "filtering_strategy": "Query params for status, date range, search",
    "error_format": {"type": "string", "title": "string", "detail": "string", "status": "integer"},
    "rate_limiting": {"default": "100/min", "auth_endpoints": "10/min"},
})


@pytest.mark.asyncio
async def test_api_contract_produces_endpoints() -> None:
    llm = _mock_llm(API_RESPONSE)
    skill = APIContractSkill(llm=llm)
    result = await skill.run(APIContractInput(
        entities=[{"entity_name": "Product"}, {"entity_name": "Order"}],
        user_workflows=[{"journey_name": "Create Order"}],
        business_rules=[{"rule_name": "order_approval"}],
    ))
    assert isinstance(result, APISpecification)
    assert len(result.endpoints) >= 2
    methods = [e.method for e in result.endpoints]
    assert "GET" in methods
    assert "POST" in methods


@pytest.mark.asyncio
async def test_api_contract_has_auth_roles() -> None:
    llm = _mock_llm(API_RESPONSE)
    skill = APIContractSkill(llm=llm)
    result = await skill.run(APIContractInput(entities=[{"entity_name": "Product"}]))
    for ep in result.endpoints:
        assert ep.auth_required
        assert len(ep.required_roles) >= 1


# ─── AuthDesignSkill ───


AUTH_RESPONSE = json.dumps({
    "auth_strategy": "jwt",
    "oauth2_flows": ["authorization_code"],
    "token_management": [
        {"type": "access", "expiry": "15m", "rotation_policy": "No rotation", "storage": "memory"},
        {"type": "refresh", "expiry": "30d", "rotation_policy": "Rotate on use", "storage": "httponly_cookie"},
    ],
    "roles": [
        {"name": "admin", "description": "Full access", "permissions": ["all"], "inherits_from": "manager"},
        {"name": "manager", "description": "Order management", "permissions": ["orders:write", "products:write"], "inherits_from": "viewer"},
        {"name": "viewer", "description": "Read only", "permissions": ["orders:read", "products:read"], "inherits_from": ""},
    ],
    "permissions": [
        {"name": "orders:write", "description": "Create/update orders", "resource": "orders", "actions": ["create", "update"]},
    ],
    "permission_matrix": {"admin": ["all"], "manager": ["orders:write", "products:write"], "viewer": ["orders:read"]},
    "middleware_design": "JWT verification middleware on all routes, role check decorator per endpoint",
    "security_measures": [
        {"measure": "Password hashing", "description": "bcrypt with cost factor 12", "configuration": "bcrypt.hashpw()"},
        {"measure": "Rate limiting", "description": "10 attempts per minute on /auth/login", "configuration": "Redis-based sliding window"},
    ],
    "password_policy": "Min 12 chars, upper+lower+digit+special",
    "session_management": "Stateless JWT, refresh token rotation, Redis blacklist for revocation",
})


@pytest.mark.asyncio
async def test_auth_design_produces_roles() -> None:
    llm = _mock_llm(AUTH_RESPONSE)
    skill = AuthDesignSkill(llm=llm)
    result = await skill.run(AuthDesignInput(
        user_roles=[{"name": "admin"}, {"name": "manager"}, {"name": "viewer"}],
        security_requirements=["Account lockout after 3 failed attempts"],
    ))
    assert isinstance(result, AuthDesign)
    assert result.auth_strategy == "jwt"
    assert len(result.roles) >= 3
    assert len(result.token_management) >= 2


@pytest.mark.asyncio
async def test_auth_design_has_security_measures() -> None:
    llm = _mock_llm(AUTH_RESPONSE)
    skill = AuthDesignSkill(llm=llm)
    result = await skill.run(AuthDesignInput(user_roles=[{"name": "admin"}]))
    assert len(result.security_measures) >= 1
    assert result.password_policy


# ─── ComponentDesignSkill ───


COMPONENT_RESPONSE = json.dumps({
    "framework": "Next.js 14",
    "routes": [
        {"path": "/dashboard", "page_component": "DashboardPage", "layout": "MainLayout", "auth_required": True, "required_roles": ["viewer", "manager", "admin"]},
        {"path": "/products", "page_component": "ProductsPage", "layout": "MainLayout", "auth_required": True, "required_roles": ["viewer", "manager", "admin"]},
    ],
    "pages": [
        {"name": "DashboardPage", "type": "page", "description": "Main dashboard", "props": [], "state": [{"name": "stats", "type": "DashboardStats", "scope": "local"}], "api_calls": ["GET /api/v1/reports/summary"], "children": ["StatsCards", "RecentOrders"], "events": []},
    ],
    "shared_components": [
        {"name": "DataTable", "type": "presentational", "description": "Reusable data table", "props": [{"name": "data", "type": "array", "required": "true", "description": "Table data"}], "state": [], "api_calls": [], "children": [], "events": ["onSort", "onFilter"]},
    ],
    "forms": [
        {"name": "CreateOrderForm", "fields": [{"name": "items", "type": "array", "validation": "required, min 1 item"}], "submit_endpoint": "POST /api/v1/orders", "validation_rules": ["At least one item required"], "error_messages": {"items": "Order must have at least one item"}},
    ],
    "state_management": "React Query for server state, Zustand for client state",
    "data_fetching": "React Query with SWR caching, optimistic updates for mutations",
    "component_tree_mermaid": "graph TD; App --> Layout; Layout --> Dashboard; Layout --> Products",
})


@pytest.mark.asyncio
async def test_component_design_produces_routes() -> None:
    llm = _mock_llm(COMPONENT_RESPONSE)
    skill = ComponentDesignSkill(llm=llm)
    result = await skill.run(ComponentDesignInput(
        user_workflows=[{"journey_name": "View Dashboard"}],
        entities=[{"entity_name": "Product"}],
        api_endpoints=[{"method": "GET", "path": "/products"}],
    ))
    assert isinstance(result, ComponentArchitecture)
    assert result.framework
    assert len(result.routes) >= 2
    assert len(result.pages) >= 1


@pytest.mark.asyncio
async def test_component_design_has_shared_components() -> None:
    llm = _mock_llm(COMPONENT_RESPONSE)
    skill = ComponentDesignSkill(llm=llm)
    result = await skill.run(ComponentDesignInput(entities=[{"entity_name": "Product"}]))
    assert len(result.shared_components) >= 1
    assert len(result.forms) >= 1
    assert result.state_management
