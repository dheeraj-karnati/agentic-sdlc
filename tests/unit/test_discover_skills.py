"""Unit tests for Discovery Agent skills."""

import pytest

from src.agents.discover.skills.code_analysis_skill import (
    CodeAnalysisInput,
    CodeAnalysisResult,
    CodeAnalysisSkill,
)
from src.agents.discover.skills.schema_analysis_skill import (
    SchemaAnalysisInput,
    SchemaAnalysisResult,
    SchemaAnalysisSkill,
)


# ─── Sample Data ───

SAMPLE_PYTHON_CODE = """\
from flask import Flask, jsonify, request
from sqlalchemy import select
import redis

app = Flask(__name__)


class UserRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_email(self, email: str) -> dict:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, email: str) -> dict:
        user = User(name=name, email=email)
        self.session.add(user)
        await self.session.flush()
        return user


class AuthService:
    MAX_ATTEMPTS = 3

    def authenticate(self, username, password):
        pass

    def refresh_token(self, token):
        pass

    def revoke_token(self, token):
        pass

    def check_permissions(self, user_id, resource):
        pass

    def create_session(self, user_id):
        pass

    def destroy_session(self, session_id):
        pass

    def validate_token(self, token):
        pass

    def generate_otp(self, user_id):
        pass

    def verify_otp(self, user_id, otp):
        pass

    def reset_password(self, user_id, new_password):
        pass

    def change_email(self, user_id, new_email):
        pass


@app.route('/api/users', methods=['GET'])
def list_users():
    return jsonify([])


@app.post('/api/users')
def create_user():
    data = request.json
    return jsonify(data), 201


@app.get('/api/health')
def health_check():
    return jsonify({"status": "ok"})


# Raw SQL query
FIND_ACTIVE_ORDERS = "SELECT * FROM orders WHERE status = 'active' AND customer_id = ?;"
"""

SAMPLE_SQL_SCHEMA = """\
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    product_id UUID NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_user_id ON orders(user_id);
"""


# ─── CodeAnalysisSkill tests ───


@pytest.mark.asyncio
async def test_code_analysis_extracts_classes() -> None:
    """CodeAnalysisSkill finds classes and their base classes."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    assert isinstance(result, CodeAnalysisResult)
    class_names = [c.name for c in result.module_structure[0].classes]
    assert "UserRepository" in class_names
    assert "AuthService" in class_names


@pytest.mark.asyncio
async def test_code_analysis_extracts_functions() -> None:
    """CodeAnalysisSkill finds function definitions."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    fn_names = [f.name for f in result.module_structure[0].functions]
    assert "list_users" in fn_names
    assert "create_user" in fn_names
    assert "health_check" in fn_names
    assert "get_by_email" in fn_names


@pytest.mark.asyncio
async def test_code_analysis_extracts_imports() -> None:
    """CodeAnalysisSkill extracts import statements."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    imports = result.module_structure[0].imports
    assert any("flask" in i.lower() for i in imports)
    assert any("redis" in i.lower() for i in imports)


@pytest.mark.asyncio
async def test_code_analysis_detects_api_endpoints() -> None:
    """CodeAnalysisSkill finds route decorators."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    paths = [e.path for e in result.api_surface]
    assert "/api/users" in paths
    assert "/api/health" in paths


@pytest.mark.asyncio
async def test_code_analysis_detects_sql_queries() -> None:
    """CodeAnalysisSkill finds raw SQL queries."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    assert len(result.database_queries) > 0
    sql_queries = [q for q in result.database_queries if q.query_type == "SELECT"]
    assert len(sql_queries) >= 1


@pytest.mark.asyncio
async def test_code_analysis_detects_technology_stack() -> None:
    """CodeAnalysisSkill identifies frameworks and libraries."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    assert "Flask" in result.technology_stack
    assert "Redis" in result.technology_stack
    assert "SQLAlchemy" in result.technology_stack


@pytest.mark.asyncio
async def test_code_analysis_detects_patterns() -> None:
    """CodeAnalysisSkill identifies design patterns."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    assert "Repository Pattern" in result.code_patterns


@pytest.mark.asyncio
async def test_code_analysis_detects_dependencies() -> None:
    """CodeAnalysisSkill builds a dependency graph from imports."""
    skill = CodeAnalysisSkill()
    result = await skill.run(CodeAnalysisInput(source_code=SAMPLE_PYTHON_CODE, language="python"))

    targets = [d.target for d in result.dependency_graph]
    assert "redis" in targets


# ─── SchemaAnalysisSkill tests ───


@pytest.mark.asyncio
async def test_schema_analysis_extracts_tables() -> None:
    """SchemaAnalysisSkill finds CREATE TABLE statements."""
    skill = SchemaAnalysisSkill()
    result = await skill.run(SchemaAnalysisInput(sql_or_schema=SAMPLE_SQL_SCHEMA))

    assert isinstance(result, SchemaAnalysisResult)
    table_names = [t.name for t in result.tables]
    assert "users" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names


@pytest.mark.asyncio
async def test_schema_analysis_extracts_columns() -> None:
    """SchemaAnalysisSkill extracts column details."""
    skill = SchemaAnalysisSkill()
    result = await skill.run(SchemaAnalysisInput(sql_or_schema=SAMPLE_SQL_SCHEMA))

    users_table = next(t for t in result.tables if t.name == "users")
    col_names = [c.name for c in users_table.columns]
    assert "id" in col_names
    assert "email" in col_names
    assert "deleted_at" in col_names


@pytest.mark.asyncio
async def test_schema_analysis_extracts_foreign_keys() -> None:
    """SchemaAnalysisSkill finds FK relationships."""
    skill = SchemaAnalysisSkill()
    result = await skill.run(SchemaAnalysisInput(sql_or_schema=SAMPLE_SQL_SCHEMA))

    assert len(result.relationships) >= 2
    fk_targets = [(r.from_table, r.to_table) for r in result.relationships]
    assert ("orders", "users") in fk_targets
    assert ("order_items", "orders") in fk_targets


@pytest.mark.asyncio
async def test_schema_analysis_detects_soft_delete() -> None:
    """SchemaAnalysisSkill detects soft delete pattern."""
    skill = SchemaAnalysisSkill()
    result = await skill.run(SchemaAnalysisInput(sql_or_schema=SAMPLE_SQL_SCHEMA))

    pattern_names = [p.pattern_name for p in result.data_patterns]
    assert "soft_delete" in pattern_names


@pytest.mark.asyncio
async def test_schema_analysis_detects_audit_columns() -> None:
    """SchemaAnalysisSkill detects audit column pattern."""
    skill = SchemaAnalysisSkill()
    result = await skill.run(SchemaAnalysisInput(sql_or_schema=SAMPLE_SQL_SCHEMA))

    pattern_names = [p.pattern_name for p in result.data_patterns]
    assert "audit_columns" in pattern_names


@pytest.mark.asyncio
async def test_schema_analysis_detects_normalization_issues() -> None:
    """SchemaAnalysisSkill flags JSONB columns as potential denormalization."""
    skill = SchemaAnalysisSkill()
    result = await skill.run(SchemaAnalysisInput(sql_or_schema=SAMPLE_SQL_SCHEMA))

    assert any("metadata" in issue.lower() for issue in result.normalization_issues)


@pytest.mark.asyncio
async def test_schema_analysis_detects_missing_constraints() -> None:
    """SchemaAnalysisSkill identifies _id columns without FK constraints."""
    skill = SchemaAnalysisSkill()
    result = await skill.run(SchemaAnalysisInput(sql_or_schema=SAMPLE_SQL_SCHEMA))

    # product_id in order_items has no FK constraint
    assert any("product_id" in m for m in result.missing_constraints)
