"""AST-lite code structure extraction for D1: Ingest.

Extracts class/method signatures, annotations, imports, embedded SQL,
hardcoded values, and key comments using regex + heuristics.
No heavy AST library needed — works across all enterprise languages.

Supports: Java, COBOL, PL/SQL, Progress 4GL, VB6/ASP, Python, C#, SQL.
"""

import logging
import re

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ─── Output models ───


class MethodSignature(BaseModel):
    name: str
    params: str = ""
    return_type: str = ""
    annotations: list[str] = Field(default_factory=list)


class HardcodedValue(BaseModel):
    name: str  # variable or constant name
    value: str  # the literal value
    line_hint: str = ""  # surrounding context


class CodeStructure(BaseModel):
    """Structured representation of a source code file."""

    language: str
    file_path: str = ""
    package: str = ""
    class_name: str = ""
    parent_class: str = ""
    interfaces: list[str] = Field(default_factory=list)
    annotations: list[str] = Field(default_factory=list)
    methods: list[MethodSignature] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    sql_queries: list[str] = Field(default_factory=list)
    hardcoded_values: list[HardcodedValue] = Field(default_factory=list)
    key_comments: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)


# ─── Extractors ───


def _extract_java(content: str, file_path: str) -> CodeStructure:
    """Extract structure from Java source."""
    cs = CodeStructure(language="java", file_path=file_path)

    # Package
    m = re.search(r"package\s+([\w.]+)\s*;", content)
    if m:
        cs.package = m.group(1)

    # Imports
    cs.imports = re.findall(r"import\s+([\w.*]+)\s*;", content)

    # Class declaration
    m = re.search(
        r"(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)"
        r"(?:\s+extends\s+(\w+))?"
        r"(?:\s+implements\s+([\w,\s]+))?",
        content,
    )
    if m:
        cs.class_name = m.group(1)
        cs.parent_class = m.group(2) or ""
        if m.group(3):
            cs.interfaces = [i.strip() for i in m.group(3).split(",")]

    # Interface declaration
    if not cs.class_name:
        m = re.search(r"(?:public\s+)?interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?", content)
        if m:
            cs.class_name = m.group(1)
            if m.group(2):
                cs.interfaces = [i.strip() for i in m.group(2).split(",")]

    # Class-level annotations
    class_annots = re.findall(r"@(\w+)(?:\([^)]*\))?\s*(?:public|abstract|final|class|interface)", content)
    cs.annotations = list(dict.fromkeys(class_annots))  # dedupe preserving order

    # Methods
    method_pattern = re.compile(
        r"(?:(@\w+(?:\([^)]*\))?)\s+)*"
        r"(?:public|protected|private)\s+"
        r"(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
        r"([\w<>\[\],\s?]+?)\s+(\w+)\s*\(([^)]*)\)",
    )
    for match in method_pattern.finditer(content):
        annot = match.group(1)
        ret = match.group(2).strip()
        name = match.group(3)
        params = match.group(4).strip()
        ms = MethodSignature(name=name, params=params, return_type=ret)
        if annot:
            ms.annotations = [annot.split("(")[0].lstrip("@")]
        cs.methods.append(ms)

    # Embedded SQL
    sql_pattern = re.compile(r'["\'](\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s[^"\']{10,})["\']', re.IGNORECASE)
    cs.sql_queries = [m.strip() for m in sql_pattern.findall(content)][:20]

    # Also catch f-string SQL (Python-style, but sometimes in Java string concat)
    fstring_sql = re.findall(r'(?:SELECT|INSERT|UPDATE|DELETE)\s+.*?\+\s*\w+', content, re.IGNORECASE)
    cs.sql_queries.extend(s.strip()[:200] for s in fstring_sql[:10])

    # Hardcoded values (thresholds, credentials)
    for m in re.finditer(r'(?:final\s+\w+\s+)?(\w+)\s*=\s*(\d{3,}|"[^"]{5,50}")', content):
        cs.hardcoded_values.append(HardcodedValue(name=m.group(1), value=m.group(2)))

    # Key comments
    for m in re.finditer(r"(?://|/\*)\s*(TODO|FIXME|HACK|XXX|BUSINESS\s*RULE|IMPORTANT)[:\s]*(.*?)(?:\*/|\n)", content, re.IGNORECASE):
        cs.key_comments.append(f"{m.group(1)}: {m.group(2).strip()}"[:200])

    # Spring bean dependencies (constructor injection)
    for m in re.finditer(r"private\s+(?:final\s+)?(\w+)\s+\w+;", content):
        dep = m.group(1)
        if dep[0].isupper() and dep not in ("String", "Integer", "Long", "Boolean", "List", "Map", "Set", "Optional"):
            cs.dependencies.append(dep)

    # Entry points
    if any(a in cs.annotations for a in ("RestController", "Controller", "WebServlet")):
        cs.entry_points = [f"HTTP endpoint: {cs.class_name}"]
    for m in re.finditer(r'@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping)\s*\(\s*["\']([^"\']+)', content):
        cs.entry_points.append(f"Endpoint: {m.group(1)}")

    # EJB / WebSphere patterns
    if re.search(r"@(?:Stateless|Stateful|MessageDriven|Singleton)", content):
        cs.annotations.append("EJB")
    if re.search(r"InitialContext|lookup\s*\(", content):
        cs.entry_points.append("JNDI lookup")

    return cs


def _extract_cobol(content: str, file_path: str) -> CodeStructure:
    """Extract structure from COBOL source."""
    cs = CodeStructure(language="cobol", file_path=file_path)

    # Program ID
    m = re.search(r"PROGRAM-ID\.\s*(\S+)", content, re.IGNORECASE)
    if m:
        cs.class_name = m.group(1).rstrip(".")

    # Copybook references
    cs.imports = re.findall(r"COPY\s+(\S+)", content, re.IGNORECASE)
    cs.imports = [c.rstrip(".") for c in cs.imports]

    # CALL targets (program dependencies)
    cs.dependencies = list(set(re.findall(r"CALL\s+'(\w+)'", content, re.IGNORECASE)))

    # Paragraph names (equivalent to methods in COBOL)
    # COBOL paragraphs: start at column 8, end with a period
    for m in re.finditer(r"^\s{7,8}(\w[\w-]+)\.\s*$", content, re.MULTILINE):
        name = m.group(1)
        # Skip division/section headers
        if not any(kw in name.upper() for kw in ("DIVISION", "SECTION", "PROGRAM-ID")):
            cs.methods.append(MethodSignature(name=name))

    # Embedded SQL (EXEC SQL ... END-EXEC)
    for m in re.finditer(r"EXEC\s+SQL(.*?)END-EXEC", content, re.IGNORECASE | re.DOTALL):
        sql = m.group(1).strip()[:300]
        cs.sql_queries.append(sql)

    # CICS commands (entry points)
    for m in re.finditer(r"EXEC\s+CICS\s+(\w+)(.*?)END-EXEC", content, re.IGNORECASE | re.DOTALL):
        cs.entry_points.append(f"CICS {m.group(1)}")

    # 88-level conditions (business rules!)
    for m in re.finditer(r"88\s+([\w-]+)\s+VALUE[S]?\s+(.*?)\.", content, re.IGNORECASE):
        cs.key_comments.append(f"BUSINESS RULE: {m.group(1)} = {m.group(2).strip()[:100]}")

    # File descriptors (VSAM/sequential)
    for m in re.finditer(r"FD\s+(\S+)", content, re.IGNORECASE):
        cs.dependencies.append(f"FILE: {m.group(1).rstrip('.')}")

    # Working-storage key variables with business-significant PIC
    for m in re.finditer(r"01\s+([\w-]+)\.", content, re.IGNORECASE):
        name = m.group(1)
        if name.upper() not in ("FILLER",):
            cs.hardcoded_values.append(HardcodedValue(name=name, value="01-level record"))

    return cs


def _extract_plsql(content: str, file_path: str) -> CodeStructure:
    """Extract structure from PL/SQL source."""
    cs = CodeStructure(language="plsql", file_path=file_path)

    # Package name
    m = re.search(r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?)?PACKAGE\s+(?:BODY\s+)?(\w+)", content, re.IGNORECASE)
    if m:
        cs.class_name = m.group(1)
        cs.package = m.group(1)

    # Procedures and functions
    for m in re.finditer(
        r"(?:PROCEDURE|FUNCTION)\s+(\w+)\s*(?:\(([^)]*)\))?\s*(?:RETURN\s+(\w+))?",
        content, re.IGNORECASE,
    ):
        ms = MethodSignature(
            name=m.group(1),
            params=m.group(2).strip() if m.group(2) else "",
            return_type=m.group(3) or "",
        )
        cs.methods.append(ms)

    # Trigger name
    for m in re.finditer(r"CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+(\w+)", content, re.IGNORECASE):
        cs.entry_points.append(f"TRIGGER: {m.group(1)}")

    # Cursor declarations (contain SELECT statements)
    for m in re.finditer(r"CURSOR\s+(\w+).*?IS\s+(SELECT.*?);", content, re.IGNORECASE | re.DOTALL):
        cs.sql_queries.append(f"CURSOR {m.group(1)}: {m.group(2).strip()[:200]}")

    # DBMS_ package calls
    for m in re.finditer(r"(DBMS_\w+)\.\w+", content, re.IGNORECASE):
        cs.dependencies.append(m.group(1))
    cs.dependencies = list(set(cs.dependencies))

    # Exception handlers
    for m in re.finditer(r"WHEN\s+(\w+)\s+THEN", content, re.IGNORECASE):
        cs.key_comments.append(f"Exception handler: {m.group(1)}")

    # %TYPE and %ROWTYPE references (entity detection)
    for m in re.finditer(r"(\w+)\.(\w+)%(?:TYPE|ROWTYPE)", content, re.IGNORECASE):
        cs.dependencies.append(f"TABLE: {m.group(1)}")
    cs.dependencies = list(set(cs.dependencies))

    return cs


def _extract_progress(content: str, file_path: str) -> CodeStructure:
    """Extract structure from Progress 4GL / OpenEdge ABL source."""
    cs = CodeStructure(language="progress_4gl", file_path=file_path)

    # Class name (if .cls)
    m = re.search(r"CLASS\s+([\w.]+)", content, re.IGNORECASE)
    if m:
        cs.class_name = m.group(1)
        cs.package = ".".join(m.group(1).split(".")[:-1])

    # Procedures
    for m in re.finditer(r"PROCEDURE\s+(\w[\w-]*)\s*:", content, re.IGNORECASE):
        cs.methods.append(MethodSignature(name=m.group(1)))

    # Functions with return types
    for m in re.finditer(r"FUNCTION\s+(\w[\w-]*)\s+RETURNS\s+(\w+)", content, re.IGNORECASE):
        cs.methods.append(MethodSignature(name=m.group(1), return_type=m.group(2)))

    # RUN statements (dependencies)
    cs.dependencies = list(set(re.findall(r"RUN\s+([\w/.-]+)", content, re.IGNORECASE)))

    # TEMP-TABLE definitions (entities)
    for m in re.finditer(r"DEFINE\s+TEMP-TABLE\s+([\w-]+)", content, re.IGNORECASE):
        cs.key_comments.append(f"TEMP-TABLE: {m.group(1)}")

    # FOR EACH queries (DB access patterns)
    for m in re.finditer(r"FOR\s+EACH\s+(\w+)(?:\s+WHERE\s+([^:]+))?", content, re.IGNORECASE):
        query = f"FOR EACH {m.group(1)}"
        if m.group(2):
            query += f" WHERE {m.group(2).strip()[:100]}"
        cs.sql_queries.append(query)

    # FIND statements
    for m in re.finditer(r"FIND\s+(?:FIRST|LAST)?\s*(\w+)", content, re.IGNORECASE):
        cs.sql_queries.append(f"FIND {m.group(1)}")

    # Include files
    cs.imports = re.findall(r"\{([\w/.-]+\.i)\}", content)

    # PUBLISH/SUBSCRIBE events
    for m in re.finditer(r"(?:PUBLISH|SUBSCRIBE)\s+[\"'](\w+)[\"']", content, re.IGNORECASE):
        cs.entry_points.append(f"EVENT: {m.group(1)}")

    return cs


def _extract_vb6(content: str, file_path: str) -> CodeStructure:
    """Extract structure from VB6 / Classic ASP source."""
    cs = CodeStructure(language="vb6", file_path=file_path)

    # Class name from filename
    cs.class_name = file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0] if "/" in file_path else file_path.rsplit(".", 1)[0]

    # Subs and Functions
    for m in re.finditer(
        r"(?:Public|Private|Friend)?\s*(?:Sub|Function)\s+(\w+)\s*\(([^)]*)\)(?:\s+As\s+(\w+))?",
        content, re.IGNORECASE,
    ):
        cs.methods.append(MethodSignature(
            name=m.group(1),
            params=m.group(2).strip(),
            return_type=m.group(3) or "",
        ))

    # ADODB / database patterns
    if re.search(r"ADODB|CreateObject\s*\(\s*[\"']ADODB", content, re.IGNORECASE):
        cs.dependencies.append("ADODB")

    # SQL strings
    for m in re.finditer(r'"((?:SELECT|INSERT|UPDATE|DELETE)\s[^"]{10,})"', content, re.IGNORECASE):
        cs.sql_queries.append(m.group(1).strip()[:200])

    # Server.CreateObject (COM deps)
    for m in re.finditer(r'Server\.CreateObject\s*\(\s*"([^"]+)"', content, re.IGNORECASE):
        cs.dependencies.append(f"COM: {m.group(1)}")

    # Hardcoded values
    for m in re.finditer(r"(?:Const|Dim)\s+(\w+)\s*=\s*(\d{3,}|\"[^\"]{5,}\")", content, re.IGNORECASE):
        cs.hardcoded_values.append(HardcodedValue(name=m.group(1), value=m.group(2)))

    return cs


def _extract_python(content: str, file_path: str) -> CodeStructure:
    """Extract structure from Python source."""
    cs = CodeStructure(language="python", file_path=file_path)

    # Module-level imports
    cs.imports = re.findall(r"(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", content)
    cs.imports = [i[0] or i[1] for i in cs.imports]

    # Class
    m = re.search(r"class\s+(\w+)(?:\(([^)]+)\))?", content)
    if m:
        cs.class_name = m.group(1)
        if m.group(2):
            parents = [p.strip() for p in m.group(2).split(",")]
            if parents:
                cs.parent_class = parents[0]
                cs.interfaces = parents[1:]

    # Decorators on class
    cs.annotations = re.findall(r"@(\w+)(?:\([^)]*\))?\s*\nclass\s", content)

    # Functions/methods
    for m in re.finditer(r"(?:@(\w+)(?:\([^)]*\))?\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\w+))?", content):
        ms = MethodSignature(
            name=m.group(2),
            params=m.group(3).strip(),
            return_type=m.group(4) or "",
        )
        if m.group(1):
            ms.annotations = [m.group(1)]
        cs.methods.append(ms)

    # SQL in strings
    for m in re.finditer(r'(?:f?["\'])((?:SELECT|INSERT|UPDATE|DELETE)\s[^"\']{10,})["\']', content, re.IGNORECASE):
        cs.sql_queries.append(m.group(1).strip()[:200])

    # Key comments
    for m in re.finditer(r"#\s*(TODO|FIXME|HACK|XXX|BUSINESS\s*RULE)[:\s]*(.*)", content, re.IGNORECASE):
        cs.key_comments.append(f"{m.group(1)}: {m.group(2).strip()}"[:200])

    # Hardcoded values
    for m in re.finditer(r"(\w+)\s*=\s*(\d{4,}|['\"][^'\"]{5,50}['\"])", content):
        name = m.group(1)
        if name.isupper() or name.startswith("_"):
            cs.hardcoded_values.append(HardcodedValue(name=name, value=m.group(2)))

    return cs


def _extract_sql(content: str, file_path: str) -> CodeStructure:
    """Extract structure from SQL files (DDL, stored procedures, migrations)."""
    cs = CodeStructure(language="sql", file_path=file_path)

    # Tables
    tables = re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", content, re.IGNORECASE)
    for t in tables:
        cs.methods.append(MethodSignature(name=f"TABLE: {t}"))

    # Views
    views = re.findall(r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)", content, re.IGNORECASE)
    for v in views:
        cs.methods.append(MethodSignature(name=f"VIEW: {v}"))

    # Stored procedures / functions
    for m in re.finditer(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION|PROC)\s+(\w+)", content, re.IGNORECASE):
        cs.methods.append(MethodSignature(name=m.group(1)))

    # Triggers
    for m in re.finditer(r"CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+(\w+)", content, re.IGNORECASE):
        cs.entry_points.append(f"TRIGGER: {m.group(1)}")

    # Indexes
    indexes = re.findall(r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)", content, re.IGNORECASE)
    for idx in indexes:
        cs.key_comments.append(f"INDEX: {idx}")

    # Key comments
    for m in re.finditer(r"--\s*(TODO|FIXME|HACK|IMPORTANT|BUSINESS\s*RULE)[:\s]*(.*)", content, re.IGNORECASE):
        cs.key_comments.append(f"{m.group(1)}: {m.group(2).strip()}"[:200])

    cs.class_name = file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0] if "/" in file_path else file_path.rsplit(".", 1)[0]

    return cs


def _extract_generic(content: str, file_path: str, language: str) -> CodeStructure:
    """Fallback extractor for unknown or config languages."""
    cs = CodeStructure(language=language, file_path=file_path)
    cs.class_name = file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0] if "/" in file_path else file_path.rsplit(".", 1)[0]

    # Try to find any SQL
    for m in re.finditer(r'(?:SELECT|INSERT|UPDATE|DELETE)\s+\w+', content, re.IGNORECASE):
        cs.sql_queries.append(m.group(0)[:200])
        if len(cs.sql_queries) >= 10:
            break

    # Key comments (// or # or --)
    for m in re.finditer(r"(?://|#|--)\s*(TODO|FIXME|HACK|XXX)[:\s]*(.*)", content, re.IGNORECASE):
        cs.key_comments.append(f"{m.group(1)}: {m.group(2).strip()}"[:200])

    return cs


# ─── Public API ───

_EXTRACTORS: dict[str, type] = {
    "java": _extract_java,
    "kotlin": _extract_java,  # close enough for structure
    "scala": _extract_java,
    "groovy": _extract_java,
    "cobol": _extract_cobol,
    "cobol_copybook": _extract_cobol,
    "plsql": _extract_plsql,
    "progress_4gl": _extract_progress,
    "progress_class": _extract_progress,
    "progress_include": _extract_progress,
    "vb6": _extract_vb6,
    "vbscript": _extract_vb6,
    "asp_classic": _extract_vb6,
    "python": _extract_python,
    "sql": _extract_sql,
    "sql_view": _extract_sql,
}


def extract_code_structure(content: str, file_path: str, language: str) -> CodeStructure:
    """Extract code structure from source content.

    Uses the deep extractor registry (Phase 4) when available,
    falling back to the inline extractors above.

    Args:
        content: Source code text.
        file_path: Relative file path (for context).
        language: Language identifier from enterprise_classifier_skill.

    Returns:
        CodeStructure with extracted metadata.
    """
    # Try deep extractors first (Phase 4)
    try:
        from src.agents.ingest.extractors import get_extractor
        extractor = get_extractor(language)
        return extractor(content, file_path)
    except Exception as e:
        logger.debug("Deep extractor failed for %s, using inline: %s", language, e)

    # Fallback to inline extractors
    extractor = _EXTRACTORS.get(language, _extract_generic)
    try:
        return extractor(content, file_path, language) if extractor == _extract_generic else extractor(content, file_path)
    except Exception as e:
        logger.warning("Code structure extraction failed for %s: %s", file_path, e)
        return CodeStructure(language=language, file_path=file_path)
