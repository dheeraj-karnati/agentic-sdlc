"""CodeParsingSkill: extracts structure from source code files."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


class SourceFile(BaseModel):
    file_path: str = ""
    content: str = ""
    language: str = ""


class FunctionDef(BaseModel):
    name: str = ""
    params: list[str] = Field(default_factory=list)
    return_type: str = ""
    line_number: int = 0


class ClassDef(BaseModel):
    name: str = ""
    bases: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)


class APIEndpoint(BaseModel):
    method: str = ""
    path: str = ""
    handler: str = ""


class CodeParsingInput(BaseModel):
    source_files: list[SourceFile] = Field(default_factory=list)


class CodebaseAnalysis(BaseModel):
    file_inventory: list[dict[str, str]] = Field(default_factory=list)
    module_structure: list[dict[str, list]] = Field(default_factory=list)
    import_graph: list[dict[str, str]] = Field(default_factory=list)
    api_endpoints: list[APIEndpoint] = Field(default_factory=list)
    database_operations: list[str] = Field(default_factory=list)
    configuration_files: list[str] = Field(default_factory=list)
    technology_stack: list[str] = Field(default_factory=list)
    total_lines: int = 0
    total_files: int = 0


_ROUTE_RE = re.compile(r'@\w+\.(?:route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE)
_IMPORT_RE = re.compile(r"^(?:from\s+[\w.]+\s+)?import\s+.+", re.MULTILINE)
_CLASS_RE = re.compile(r"^class\s+(\w+)\s*(?:\(([^)]*)\))?:", re.MULTILINE)
_FUNC_RE = re.compile(r"^(?:\s*)(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
_SQL_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE)\b", re.IGNORECASE)

_CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"}
_TECH_PATTERNS = {
    "Flask": re.compile(r"\bFlask\b|from flask"),
    "FastAPI": re.compile(r"\bFastAPI\b|from fastapi"),
    "Django": re.compile(r"\bdjango\b", re.I),
    "React": re.compile(r"from ['\"]react['\"]|import React"),
    "Express": re.compile(r"require\(['\"]express['\"]\)"),
    "SQLAlchemy": re.compile(r"\bsqlalchemy\b", re.I),
    "PostgreSQL": re.compile(r"\bpostgres\b|\basyncpg\b", re.I),
    "Redis": re.compile(r"\bredis\b", re.I),
}


class CodeParsingSkill(BaseSkill[CodeParsingInput, CodebaseAnalysis]):
    """Extracts structural information from source code files."""

    name = "code_parsing"
    description = "Parse source code to extract structure, imports, endpoints, and technology stack"
    input_model = CodeParsingInput
    output_model = CodebaseAnalysis

    async def execute(self, input_data: CodeParsingInput) -> CodebaseAnalysis:
        inventory: list[dict[str, str]] = []
        modules: list[dict[str, list]] = []
        imports: list[dict[str, str]] = []
        endpoints: list[APIEndpoint] = []
        db_ops: list[str] = []
        config_files: list[str] = []
        tech: set[str] = set()
        total_lines = 0

        for sf in input_data.source_files:
            total_lines += sf.content.count("\n") + 1
            ext = "." + sf.file_path.rsplit(".", 1)[-1] if "." in sf.file_path else ""

            inventory.append({
                "file_path": sf.file_path,
                "language": sf.language,
                "lines": str(sf.content.count("\n") + 1),
            })

            if ext in _CONFIG_EXTENSIONS:
                config_files.append(sf.file_path)

            # Extract structure
            classes = [m.group(1) for m in _CLASS_RE.finditer(sf.content)]
            functions = [m.group(1) for m in _FUNC_RE.finditer(sf.content)]
            modules.append({"file": [sf.file_path], "classes": classes, "functions": functions})

            # Imports
            for m in _IMPORT_RE.finditer(sf.content):
                line = m.group(0).strip()
                if line.startswith("from "):
                    parts = line.split()
                    if len(parts) >= 4:
                        imports.append({"source": sf.file_path, "target": parts[1]})

            # API endpoints
            for m in _ROUTE_RE.finditer(sf.content):
                path = m.group(1)
                method = "GET"
                for verb in ("post", "put", "delete", "patch"):
                    if verb in m.group(0).lower():
                        method = verb.upper()
                        break
                endpoints.append(APIEndpoint(method=method, path=path))

            # Database operations
            for m in _SQL_RE.finditer(sf.content):
                db_ops.append(m.group(0))

            # Technology detection
            for name, pattern in _TECH_PATTERNS.items():
                if pattern.search(sf.content):
                    tech.add(name)

        return CodebaseAnalysis(
            file_inventory=inventory,
            module_structure=modules,
            import_graph=imports,
            api_endpoints=endpoints,
            database_operations=list(set(db_ops)),
            configuration_files=config_files,
            technology_stack=sorted(tech),
            total_lines=total_lines,
            total_files=len(input_data.source_files),
        )
