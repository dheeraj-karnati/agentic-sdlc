"""SchemaDesignSkill: generates production-quality database schemas."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class TableDesign(BaseModel):
    name: str = ""
    purpose: str = ""
    columns: list[dict[str, str]] = Field(default_factory=list)  # {name, type, constraints, description}
    primary_key: list[str] = Field(default_factory=list)
    indexes: list[dict[str, Any]] = Field(default_factory=list)  # {name, columns, unique, purpose}
    constraints: list[str] = Field(default_factory=list)  # CHECK, UNIQUE, etc.


class MigrationFile(BaseModel):
    version: str = ""
    description: str = ""
    up_sql: str = ""
    down_sql: str = ""


class SchemaDesignInput(BaseModel):
    entities: list[dict[str, Any]] = Field(default_factory=list)
    business_rules: list[dict[str, Any]] = Field(default_factory=list)
    database_type: str = "postgresql"


class DatabaseSchema(BaseModel):
    tables: list[TableDesign] = Field(default_factory=list)
    ddl: str = ""  # Complete CREATE TABLE statements
    indexes_ddl: str = ""  # CREATE INDEX statements
    er_diagram_mermaid: str = ""
    migrations: list[MigrationFile] = Field(default_factory=list)
    design_notes: list[str] = Field(default_factory=list)


_SYSTEM_PROMPT = """\
You are a senior database architect designing a production PostgreSQL schema.

Generate a complete, normalized database schema. Requirements:
- ALL tables must have: id UUID PRIMARY KEY DEFAULT gen_random_uuid()
- ALL tables must have audit columns: created_at TIMESTAMPTZ DEFAULT NOW(), \
updated_at TIMESTAMPTZ DEFAULT NOW()
- Tables with user-created data must have: created_by UUID REFERENCES users(id)
- Use soft delete (deleted_at TIMESTAMPTZ) where appropriate
- Proper NOT NULL constraints on required fields
- UNIQUE constraints where business rules require uniqueness
- CHECK constraints for enum-like columns and value ranges
- Foreign keys with appropriate ON DELETE behavior
- Indexes on: foreign keys, frequently filtered columns, unique constraints
- Use proper PostgreSQL types: UUID, TIMESTAMPTZ, DECIMAL(precision,scale), \
TEXT, VARCHAR(n), JSONB, BOOLEAN, INTEGER

## Example: Shallow vs Production Schema

BAD (shallow):
```sql
CREATE TABLE orders (id INT, user_id INT, total FLOAT, status TEXT);
```

GOOD (production):
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status VARCHAR(50) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','pending','confirmed','shipped','delivered','cancelled')),
    total_amount DECIMAL(12,2) NOT NULL CHECK (total_amount >= 0),
    discount DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    tax DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (tax >= 0),
    notes TEXT,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

Return JSON with:
- tables: list of table designs with columns, indexes, constraints
- ddl: complete CREATE TABLE SQL statements
- indexes_ddl: all CREATE INDEX statements
- er_diagram_mermaid: Mermaid ER diagram
- migrations: list of {version, description, up_sql, down_sql}
- design_notes: important design decisions and rationale"""


class SchemaDesignSkill(BaseSkill[SchemaDesignInput, DatabaseSchema]):
    """Generates production-quality normalized database schemas."""

    name = "schema_design"
    description = "Generate complete normalized database schema with indexes, constraints, and migrations"
    input_model = SchemaDesignInput
    output_model = DatabaseSchema

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: SchemaDesignInput) -> DatabaseSchema:
        llm = self._llm or get_llm(max_tokens=8192)

        schema_json = json.dumps(DatabaseSchema.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        user_content = (
            f"## Domain Entities\n{json.dumps(input_data.entities[:30], indent=2, default=str)}"
            f"\n\n## Business Rules\n{json.dumps(input_data.business_rules[:30], indent=2, default=str)}"
            f"\n\nDatabase: {input_data.database_type}"
        )

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        return DatabaseSchema.model_validate(parsed)
