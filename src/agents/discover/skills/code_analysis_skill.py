"""CodeAnalysisSkill: extracts structural information from source code.

Uses regex-based extraction to identify modules, dependencies, API surfaces,
database queries, technology stack, design patterns, and code smells.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill


# ─── Input / Output Models ───


class FunctionSignature(BaseModel):
    name: str
    params: list[str] = Field(default_factory=list)
    return_type: str = ""
    decorators: list[str] = Field(default_factory=list)


class ClassInfo(BaseModel):
    name: str
    bases: list[str] = Field(default_factory=list)
    methods: list[FunctionSignature] = Field(default_factory=list)


class ModuleStructure(BaseModel):
    file_path: str = ""
    classes: list[ClassInfo] = Field(default_factory=list)
    functions: list[FunctionSignature] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)


class DependencyEdge(BaseModel):
    source: str
    target: str
    import_type: str = "import"  # import, from_import, dynamic


class ApiEndpoint(BaseModel):
    method: str = ""  # GET, POST, etc.
    path: str = ""
    handler: str = ""
    params: list[str] = Field(default_factory=list)


class DatabaseQuery(BaseModel):
    query_type: str = ""  # SELECT, INSERT, UPDATE, DELETE, ORM
    raw_text: str = ""
    tables_referenced: list[str] = Field(default_factory=list)


class CodeSmell(BaseModel):
    smell_type: str  # large_function, god_class, circular_dep, etc.
    location: str = ""
    description: str = ""
    severity: str = "warning"  # info, warning, critical


class CodeAnalysisInput(BaseModel):
    source_code: str
    language: str = "python"


class CodeAnalysisResult(BaseModel):
    module_structure: list[ModuleStructure] = Field(default_factory=list)
    dependency_graph: list[DependencyEdge] = Field(default_factory=list)
    api_surface: list[ApiEndpoint] = Field(default_factory=list)
    database_queries: list[DatabaseQuery] = Field(default_factory=list)
    technology_stack: list[str] = Field(default_factory=list)
    code_patterns: list[str] = Field(default_factory=list)
    code_smells: list[CodeSmell] = Field(default_factory=list)


# ─── Regex Patterns ───

_PYTHON_CLASS_RE = re.compile(
    r"^class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:", re.MULTILINE
)
_PYTHON_FUNC_RE = re.compile(
    r"^(?:    |\t)?(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^\s:]+))?\s*:",
    re.MULTILINE,
)
_PYTHON_DECORATOR_RE = re.compile(r"^(\s*)@(\w[\w.]*(?:\([^)]*\))?)", re.MULTILINE)
_PYTHON_IMPORT_RE = re.compile(
    r"^(?:from\s+[\w.]+\s+)?import\s+.+", re.MULTILINE
)
_SQL_QUERY_RE = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b[^;]{5,};?",
    re.IGNORECASE | re.DOTALL,
)
_ORM_QUERY_RE = re.compile(
    r"\b(?:session|db|query|select|filter|filter_by|join|execute)\s*\(", re.IGNORECASE
)
_ROUTE_DECORATOR_RE = re.compile(
    r'@\w+\.(?:route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_TABLE_NAME_RE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+[`\"]?(\w+)[`\"]?", re.IGNORECASE
)

# Technology detection patterns
_TECH_PATTERNS: dict[str, re.Pattern[str]] = {
    "FastAPI": re.compile(r"\bFastAPI\b|from\s+fastapi\b"),
    "Flask": re.compile(r"\bFlask\b|from\s+flask\b"),
    "Django": re.compile(r"\bdjango\b", re.IGNORECASE),
    "SQLAlchemy": re.compile(r"\bSQLAlchemy\b|from\s+sqlalchemy\b", re.IGNORECASE),
    "React": re.compile(r"\bReact\b|from\s+['\"]react['\"]"),
    "Express": re.compile(r"\bexpress\b|require\(['\"]express['\"]\)"),
    "Spring": re.compile(r"\bSpringBoot\b|@SpringBootApplication"),
    "PostgreSQL": re.compile(r"\bpostgresql\b|\bpsycopg\b|\basyncpg\b", re.IGNORECASE),
    "Redis": re.compile(r"\bredis\b", re.IGNORECASE),
    "Docker": re.compile(r"\bDockerfile\b|\bdocker-compose\b"),
    "JWT": re.compile(r"\bJWT\b|\bjsonwebtoken\b|\bPyJWT\b"),
    "OAuth": re.compile(r"\bOAuth\b|\boauth2\b", re.IGNORECASE),
    "GraphQL": re.compile(r"\bgraphql\b|\bGraphQL\b"),
    "REST": re.compile(r"\bREST\b|\bapi.*endpoint\b", re.IGNORECASE),
    "Celery": re.compile(r"\bcelery\b|\bCelery\b"),
    "RabbitMQ": re.compile(r"\brabbitmq\b|\bamqp\b", re.IGNORECASE),
    "Kafka": re.compile(r"\bkafka\b", re.IGNORECASE),
}

# Design pattern detection
_PATTERN_INDICATORS: dict[str, re.Pattern[str]] = {
    "Repository Pattern": re.compile(r"\bRepository\b.*class|class.*Repository\b"),
    "Service Layer": re.compile(r"\bService\b.*class|class.*Service\b"),
    "Factory Pattern": re.compile(r"\bcreate_\w+|Factory\b.*class|class.*Factory\b"),
    "MVC": re.compile(r"\b(?:Controller|View|Model)\b.*class"),
    "Observer/Event": re.compile(r"\b(?:EventHandler|Listener|Observer|emit|subscribe)\b"),
    "Singleton": re.compile(r"_instance\s*=|__new__.*cls\._instance"),
    "Middleware": re.compile(r"\bmiddleware\b", re.IGNORECASE),
    "Dependency Injection": re.compile(r"\bDepends\b|\bInject\b|\b@inject\b"),
}


class CodeAnalysisSkill(BaseSkill[CodeAnalysisInput, CodeAnalysisResult]):
    """Extracts structural information from source code using regex analysis."""

    name = "code_analysis"
    description = "Analyze source code to extract structure, dependencies, APIs, and patterns"
    input_model = CodeAnalysisInput
    output_model = CodeAnalysisResult

    async def execute(self, input_data: CodeAnalysisInput) -> CodeAnalysisResult:
        code = input_data.source_code
        lang = input_data.language.lower()

        module = self._extract_module_structure(code, lang)
        deps = self._extract_dependencies(code)
        apis = self._extract_api_surface(code)
        queries = self._extract_database_queries(code)
        tech = self._detect_technology_stack(code)
        patterns = self._detect_code_patterns(code)
        smells = self._detect_code_smells(code, module)

        return CodeAnalysisResult(
            module_structure=[module],
            dependency_graph=deps,
            api_surface=apis,
            database_queries=queries,
            technology_stack=tech,
            code_patterns=patterns,
            code_smells=smells,
        )

    def _extract_module_structure(
        self, code: str, lang: str
    ) -> ModuleStructure:
        classes: list[ClassInfo] = []
        functions: list[FunctionSignature] = []
        imports: list[str] = []

        if lang in ("python", "py"):
            # Extract imports
            for m in _PYTHON_IMPORT_RE.finditer(code):
                imports.append(m.group(0).strip())

            # Extract classes
            for m in _PYTHON_CLASS_RE.finditer(code):
                class_name = m.group(1)
                bases = [b.strip() for b in (m.group(2) or "").split(",") if b.strip()]
                classes.append(ClassInfo(name=class_name, bases=bases))

            # Extract functions (top-level and methods)
            for m in _PYTHON_FUNC_RE.finditer(code):
                fn = FunctionSignature(
                    name=m.group(1),
                    params=[p.strip() for p in m.group(2).split(",") if p.strip()],
                    return_type=m.group(3) or "",
                )
                functions.append(fn)

        return ModuleStructure(
            classes=classes, functions=functions, imports=imports
        )

    def _extract_dependencies(self, code: str) -> list[DependencyEdge]:
        edges: list[DependencyEdge] = []
        for m in _PYTHON_IMPORT_RE.finditer(code):
            line = m.group(0).strip()
            if line.startswith("from "):
                parts = line.split()
                if len(parts) >= 4:
                    edges.append(DependencyEdge(
                        source="current_module",
                        target=parts[1],
                        import_type="from_import",
                    ))
            elif line.startswith("import "):
                modules = line.replace("import ", "").split(",")
                for mod in modules:
                    edges.append(DependencyEdge(
                        source="current_module",
                        target=mod.strip().split(" as ")[0],
                        import_type="import",
                    ))
        return edges

    def _extract_api_surface(self, code: str) -> list[ApiEndpoint]:
        endpoints: list[ApiEndpoint] = []
        for m in _ROUTE_DECORATOR_RE.finditer(code):
            path = m.group(1)
            # Determine HTTP method from decorator
            decorator_text = m.group(0).lower()
            method = "GET"
            for verb in ("post", "put", "delete", "patch"):
                if verb in decorator_text:
                    method = verb.upper()
                    break

            # Try to find the function name on the next line
            start = m.end()
            func_match = re.search(r"def\s+(\w+)", code[start : start + 200])
            handler = func_match.group(1) if func_match else ""

            endpoints.append(ApiEndpoint(method=method, path=path, handler=handler))
        return endpoints

    def _extract_database_queries(self, code: str) -> list[DatabaseQuery]:
        queries: list[DatabaseQuery] = []

        # Raw SQL
        for m in _SQL_QUERY_RE.finditer(code):
            query_text = m.group(0).strip()
            query_type = m.group(1).upper()
            tables = _TABLE_NAME_RE.findall(query_text)
            queries.append(DatabaseQuery(
                query_type=query_type,
                raw_text=query_text[:500],
                tables_referenced=list(set(tables)),
            ))

        # ORM patterns
        for m in _ORM_QUERY_RE.finditer(code):
            start = max(0, m.start() - 100)
            context = code[start : m.end() + 100]
            queries.append(DatabaseQuery(
                query_type="ORM",
                raw_text=context.strip()[:300],
            ))

        return queries

    def _detect_technology_stack(self, code: str) -> list[str]:
        detected: list[str] = []
        for tech_name, pattern in _TECH_PATTERNS.items():
            if pattern.search(code):
                detected.append(tech_name)
        return sorted(detected)

    def _detect_code_patterns(self, code: str) -> list[str]:
        patterns: list[str] = []
        for pattern_name, regex in _PATTERN_INDICATORS.items():
            if regex.search(code):
                patterns.append(pattern_name)
        return patterns

    def _detect_code_smells(
        self, code: str, module: ModuleStructure
    ) -> list[CodeSmell]:
        smells: list[CodeSmell] = []

        # Large functions (> 50 lines between def statements)
        lines = code.split("\n")
        func_starts: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            m = re.match(r"\s*(?:async\s+)?def\s+(\w+)", line)
            if m:
                func_starts.append((i, m.group(1)))

        for idx, (start_line, fn_name) in enumerate(func_starts):
            end_line = func_starts[idx + 1][0] if idx + 1 < len(func_starts) else len(lines)
            length = end_line - start_line
            if length > 50:
                smells.append(CodeSmell(
                    smell_type="large_function",
                    location=f"line {start_line + 1}",
                    description=f"Function '{fn_name}' is {length} lines long (> 50)",
                    severity="warning",
                ))

        # God classes (> 10 methods)
        for cls in module.classes:
            method_count = sum(
                1 for fn in module.functions if fn.name != "__init__"
            )
            if method_count > 10:
                smells.append(CodeSmell(
                    smell_type="god_class",
                    location=cls.name,
                    description=f"Class '{cls.name}' may have too many responsibilities",
                    severity="warning",
                ))

        return smells
