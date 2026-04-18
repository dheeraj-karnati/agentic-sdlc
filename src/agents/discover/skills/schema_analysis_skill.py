"""SchemaAnalysisSkill: parses SQL/schema definitions to extract structure."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


class ColumnInfo(BaseModel):
    name: str = ""
    data_type: str = ""
    nullable: bool = True
    default: str = ""
    constraints: list[str] = Field(default_factory=list)  # PK, UNIQUE, CHECK, etc.


class IndexInfo(BaseModel):
    name: str = ""
    columns: list[str] = Field(default_factory=list)
    unique: bool = False


class TableInfo(BaseModel):
    name: str = ""
    columns: list[ColumnInfo] = Field(default_factory=list)
    indexes: list[IndexInfo] = Field(default_factory=list)
    primary_key: list[str] = Field(default_factory=list)


class ForeignKeyRelationship(BaseModel):
    from_table: str = ""
    from_column: str = ""
    to_table: str = ""
    to_column: str = ""
    cardinality: str = ""  # 1:1, 1:N, N:M


class DataPattern(BaseModel):
    pattern_name: str = ""  # soft_delete, audit_columns, polymorphism, etc.
    evidence: str = ""
    tables_involved: list[str] = Field(default_factory=list)


class SchemaAnalysisInput(BaseModel):
    sql_or_schema: str


class SchemaAnalysisResult(BaseModel):
    tables: list[TableInfo] = Field(default_factory=list)
    relationships: list[ForeignKeyRelationship] = Field(default_factory=list)
    data_patterns: list[DataPattern] = Field(default_factory=list)
    normalization_issues: list[str] = Field(default_factory=list)
    missing_constraints: list[str] = Field(default_factory=list)


# ─── Regex Patterns for SQL Parsing ───

_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
_FK_RE = re.compile(
    r"FOREIGN\s+KEY\s*\((\w+)\)\s*REFERENCES\s+[`\"]?(\w+)[`\"]?\s*\((\w+)\)",
    re.IGNORECASE,
)
_PK_RE = re.compile(r"PRIMARY\s+KEY\s*\(([^)]+)\)", re.IGNORECASE)
_INDEX_RE = re.compile(
    r"CREATE\s+(UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?\s+ON\s+[`\"]?(\w+)[`\"]?\s*\(([^)]+)\)",
    re.IGNORECASE,
)

# Data pattern indicators
_SOFT_DELETE_COLS = {"deleted_at", "is_deleted", "deleted", "archived_at"}
_AUDIT_COLS = {"created_at", "updated_at", "created_by", "updated_by"}
_POLYMORPHIC_COLS = {"type", "kind", "discriminator", "entity_type"}


class SchemaAnalysisSkill(BaseSkill[SchemaAnalysisInput, SchemaAnalysisResult]):
    """Parses SQL DDL to extract tables, relationships, patterns, and issues."""

    name = "schema_analysis"
    description = "Analyze SQL schema to extract tables, relationships, and data patterns"
    input_model = SchemaAnalysisInput
    output_model = SchemaAnalysisResult

    async def execute(self, input_data: SchemaAnalysisInput) -> SchemaAnalysisResult:
        sql = input_data.sql_or_schema
        tables = self._extract_tables(sql)
        relationships = self._extract_relationships(sql)
        indexes = self._extract_indexes(sql)
        patterns = self._detect_data_patterns(tables)
        issues = self._check_normalization(tables)
        missing = self._check_missing_constraints(tables, relationships)

        # Attach indexes to their tables
        table_map = {t.name: t for t in tables}
        for idx in indexes:
            table_name = idx.pop("table", "")  # type: ignore[union-attr]
            if table_name in table_map:
                table_map[table_name].indexes.append(
                    IndexInfo(**idx)  # type: ignore[arg-type]
                )

        return SchemaAnalysisResult(
            tables=tables,
            relationships=relationships,
            data_patterns=patterns,
            normalization_issues=issues,
            missing_constraints=missing,
        )

    def _extract_tables(self, sql: str) -> list[TableInfo]:
        tables: list[TableInfo] = []
        for m in _CREATE_TABLE_RE.finditer(sql):
            table_name = m.group(1)
            body = m.group(2)
            columns, pk_cols = self._parse_table_body(body)
            tables.append(TableInfo(
                name=table_name, columns=columns, primary_key=pk_cols
            ))
        return tables

    def _parse_table_body(
        self, body: str
    ) -> tuple[list[ColumnInfo], list[str]]:
        columns: list[ColumnInfo] = []
        pk_cols: list[str] = []

        # Split on commas, but respect parentheses
        parts = self._split_table_body(body)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            upper = part.upper()

            # Table-level PRIMARY KEY
            pk_match = _PK_RE.search(part)
            if pk_match:
                pk_cols = [c.strip().strip("`\"") for c in pk_match.group(1).split(",")]
                continue

            # Skip FK constraints, UNIQUE constraints, CHECK constraints
            if upper.startswith(("FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "INDEX")):
                continue

            # Column definition
            col = self._parse_column(part)
            if col:
                columns.append(col)
                if "PRIMARY KEY" in upper:
                    pk_cols.append(col.name)

        return columns, pk_cols

    def _split_table_body(self, body: str) -> list[str]:
        """Split column definitions on commas, respecting parentheses."""
        parts: list[str] = []
        depth = 0
        current: list[str] = []
        for char in body:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append("".join(current))
                current = []
                continue
            current.append(char)
        if current:
            parts.append("".join(current))
        return parts

    def _parse_column(self, definition: str) -> ColumnInfo | None:
        """Parse a single column definition."""
        tokens = definition.split()
        if len(tokens) < 2:
            return None

        name = tokens[0].strip("`\"")
        # Skip if it looks like a constraint keyword
        if name.upper() in (
            "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "INDEX",
        ):
            return None

        data_type = tokens[1]
        # Handle types like VARCHAR(255)
        if len(tokens) > 2 and tokens[2].startswith("("):
            data_type += tokens[2]

        upper_def = definition.upper()
        nullable = "NOT NULL" not in upper_def
        constraints: list[str] = []

        if "PRIMARY KEY" in upper_def:
            constraints.append("PRIMARY KEY")
        if "UNIQUE" in upper_def:
            constraints.append("UNIQUE")
        if "NOT NULL" in upper_def:
            constraints.append("NOT NULL")
        if "DEFAULT" in upper_def:
            constraints.append("DEFAULT")
            # Extract default value
            default_match = re.search(r"DEFAULT\s+(\S+)", definition, re.IGNORECASE)
            default_val = default_match.group(1) if default_match else ""
        else:
            default_val = ""
        if "REFERENCES" in upper_def:
            constraints.append("FOREIGN KEY")

        return ColumnInfo(
            name=name,
            data_type=data_type,
            nullable=nullable,
            default=default_val,
            constraints=constraints,
        )

    def _extract_relationships(self, sql: str) -> list[ForeignKeyRelationship]:
        relationships: list[ForeignKeyRelationship] = []

        for table_match in _CREATE_TABLE_RE.finditer(sql):
            from_table = table_match.group(1)
            body = table_match.group(2)

            for fk in _FK_RE.finditer(body):
                relationships.append(ForeignKeyRelationship(
                    from_table=from_table,
                    from_column=fk.group(1),
                    to_table=fk.group(2),
                    to_column=fk.group(3),
                    cardinality="N:1",  # FK default assumption
                ))

        return relationships

    def _extract_indexes(self, sql: str) -> list[dict]:
        indexes: list[dict] = []
        for m in _INDEX_RE.finditer(sql):
            indexes.append({
                "name": m.group(2),
                "columns": [c.strip().strip("`\"") for c in m.group(4).split(",")],
                "unique": m.group(1) is not None,
                "table": m.group(3),
            })
        return indexes

    def _detect_data_patterns(self, tables: list[TableInfo]) -> list[DataPattern]:
        patterns: list[DataPattern] = []
        for table in tables:
            col_names = {c.name.lower() for c in table.columns}

            # Soft delete
            soft_delete = col_names & _SOFT_DELETE_COLS
            if soft_delete:
                patterns.append(DataPattern(
                    pattern_name="soft_delete",
                    evidence=f"Columns: {', '.join(soft_delete)}",
                    tables_involved=[table.name],
                ))

            # Audit columns
            audit = col_names & _AUDIT_COLS
            if len(audit) >= 2:
                patterns.append(DataPattern(
                    pattern_name="audit_columns",
                    evidence=f"Columns: {', '.join(audit)}",
                    tables_involved=[table.name],
                ))

            # Polymorphism
            poly = col_names & _POLYMORPHIC_COLS
            if poly:
                patterns.append(DataPattern(
                    pattern_name="polymorphism",
                    evidence=f"Discriminator columns: {', '.join(poly)}",
                    tables_involved=[table.name],
                ))

        return patterns

    def _check_normalization(self, tables: list[TableInfo]) -> list[str]:
        issues: list[str] = []
        for table in tables:
            for col in table.columns:
                col_type = col.data_type.upper()
                # JSON columns may indicate denormalization
                if col_type in ("JSON", "JSONB"):
                    issues.append(
                        f"Table '{table.name}' column '{col.name}' uses {col_type} "
                        f"— may indicate denormalized data that could benefit from "
                        f"a separate table"
                    )
        return issues

    def _check_missing_constraints(
        self,
        tables: list[TableInfo],
        relationships: list[ForeignKeyRelationship],
    ) -> list[str]:
        missing: list[str] = []
        fk_columns = {
            (r.from_table, r.from_column) for r in relationships
        }

        for table in tables:
            for col in table.columns:
                name_lower = col.name.lower()
                # Columns ending in _id without FK constraint
                if (
                    name_lower.endswith("_id")
                    and (table.name, col.name) not in fk_columns
                    and "PRIMARY KEY" not in col.constraints
                ):
                    missing.append(
                        f"Table '{table.name}' column '{col.name}' looks like a "
                        f"foreign key but has no FK constraint"
                    )

                # Email columns without constraints
                if "email" in name_lower and "UNIQUE" not in col.constraints:
                    missing.append(
                        f"Table '{table.name}' column '{col.name}' may need a "
                        f"UNIQUE constraint"
                    )

        return missing
