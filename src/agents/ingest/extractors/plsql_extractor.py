"""Deep Oracle PL/SQL code structure extractor for D1: Ingest.

Extracts package specs/bodies, procedures, functions, triggers, cursors,
dynamic SQL, DBMS_* usage, UTL_* file I/O, scheduler jobs, queue operations,
TYPE definitions, GRANT statements, exception handlers, bulk operations,
pipelined functions, deterministic hints, autonomous transactions,
REF CURSOR return types, global temporary tables, INSTEAD OF triggers,
%TYPE/%ROWTYPE references, and package-level constants/variables.

Uses only regex — no Oracle client or AST library required.
"""

import re
from typing import Final

from src.agents.ingest.skills.code_structure_skill import (
    CodeStructure,
    HardcodedValue,
    MethodSignature,
)

# Pre-compiled patterns for performance

_PKG_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?)?PACKAGE\s+(?:BODY\s+)?(?:\w+\.)?(\w+)",
    re.IGNORECASE,
)

_PROC_FUNC_RE: Final[re.Pattern[str]] = re.compile(
    r"(PROCEDURE|FUNCTION)\s+(\w+)\s*(?:\(([^)]*)\))?"
    r"\s*(?:RETURN\s+([\w%.]+(?:\s*%\s*(?:TYPE|ROWTYPE))?))?",
    re.IGNORECASE,
)

_TRIGGER_RE: Final[re.Pattern[str]] = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+(?:\w+\.)?(\w+)",
    re.IGNORECASE,
)

_INSTEAD_OF_TRIGGER_RE: Final[re.Pattern[str]] = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+(?:\w+\.)?(\w+)"
    r"\s+INSTEAD\s+OF\s+(\w+)\s+ON\s+(\w+)",
    re.IGNORECASE,
)

_CURSOR_RE: Final[re.Pattern[str]] = re.compile(
    r"CURSOR\s+(\w+)(?:\s*\([^)]*\))?\s+IS\s+(SELECT\b.*?);",
    re.IGNORECASE | re.DOTALL,
)

_DBMS_PKG_RE: Final[re.Pattern[str]] = re.compile(
    r"(DBMS_\w+)\.\w+", re.IGNORECASE
)

_UTL_PKG_RE: Final[re.Pattern[str]] = re.compile(
    r"(UTL_\w+)\.\w+", re.IGNORECASE
)

_UTL_FILE_OPS_RE: Final[re.Pattern[str]] = re.compile(
    r"UTL_FILE\.(FOPEN|FCLOSE|PUT_LINE|GET_LINE|PUT|FFLUSH|IS_OPEN|"
    r"FREMOVE|FRENAME|FCOPY|FGETATTR|READ|WRITE)\b",
    re.IGNORECASE,
)

_TYPE_ROWTYPE_RE: Final[re.Pattern[str]] = re.compile(
    r"(\w+)\.(\w+)\s*%\s*(TYPE|ROWTYPE)", re.IGNORECASE
)

_EXCEPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"WHEN\s+([\w]+)\s+THEN", re.IGNORECASE
)

_EXECUTE_IMMEDIATE_RE: Final[re.Pattern[str]] = re.compile(
    r"EXECUTE\s+IMMEDIATE\s+(.*?);", re.IGNORECASE | re.DOTALL
)

_PRAGMA_AUTONOMOUS_RE: Final[re.Pattern[str]] = re.compile(
    r"PRAGMA\s+AUTONOMOUS_TRANSACTION", re.IGNORECASE
)

_BULK_COLLECT_RE: Final[re.Pattern[str]] = re.compile(
    r"BULK\s+COLLECT\s+INTO\s+(\w+)", re.IGNORECASE
)

_FORALL_RE: Final[re.Pattern[str]] = re.compile(
    r"FORALL\s+(\w+)\s+IN\b", re.IGNORECASE
)

_REF_CURSOR_RE: Final[re.Pattern[str]] = re.compile(
    r"(SYS_REFCURSOR|REF\s+CURSOR)", re.IGNORECASE
)

_TYPE_TABLE_OF_RE: Final[re.Pattern[str]] = re.compile(
    r"TYPE\s+(\w+)\s+IS\s+TABLE\s+OF\b[^;]*", re.IGNORECASE
)

_TYPE_RECORD_RE: Final[re.Pattern[str]] = re.compile(
    r"TYPE\s+(\w+)\s+IS\s+RECORD\b[^;]*", re.IGNORECASE
)

_TYPE_OBJECT_RE: Final[re.Pattern[str]] = re.compile(
    r"TYPE\s+(\w+)\s+AS\s+OBJECT\b", re.IGNORECASE
)

_PIPELINED_RE: Final[re.Pattern[str]] = re.compile(
    r"FUNCTION\s+(\w+)\b[^;]*?\bPIPELINED\b", re.IGNORECASE | re.DOTALL
)

_DETERMINISTIC_RE: Final[re.Pattern[str]] = re.compile(
    r"FUNCTION\s+(\w+)\b[^;]*?\bDETERMINISTIC\b", re.IGNORECASE | re.DOTALL
)

_RESULT_CACHE_RE: Final[re.Pattern[str]] = re.compile(
    r"FUNCTION\s+(\w+)\b[^;]*?\bRESULT_CACHE\b", re.IGNORECASE | re.DOTALL
)

_SCHEDULER_JOB_RE: Final[re.Pattern[str]] = re.compile(
    r"DBMS_SCHEDULER\.(CREATE_JOB|CREATE_PROGRAM)\s*\(", re.IGNORECASE
)

_SCHEDULER_JOB_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"DBMS_SCHEDULER\.(?:CREATE_JOB|CREATE_PROGRAM)\s*\([^)]*?"
    r"job_name\s*=>\s*['\"](\w+)['\"]",
    re.IGNORECASE | re.DOTALL,
)

_AQ_RE: Final[re.Pattern[str]] = re.compile(
    r"DBMS_AQ\.(ENQUEUE|DEQUEUE)\s*\(", re.IGNORECASE
)

_AQ_QUEUE_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"DBMS_AQ\.(?:ENQUEUE|DEQUEUE)\s*\([^)]*?"
    r"queue_name\s*=>\s*['\"](\w+)['\"]",
    re.IGNORECASE | re.DOTALL,
)

_GTT_RE: Final[re.Pattern[str]] = re.compile(
    r"GLOBAL\s+TEMPORARY\s+TABLE\s+(?:\w+\.)?(\w+)\s+.*?"
    r"ON\s+COMMIT\s+(DELETE|PRESERVE)\s+ROWS",
    re.IGNORECASE | re.DOTALL,
)

_GTT_REF_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:FROM|INTO|UPDATE|JOIN)\s+(?:\w+\.)?(\w+)",
    re.IGNORECASE,
)

_GRANT_RE: Final[re.Pattern[str]] = re.compile(
    r"GRANT\s+([\w,\s]+)\s+ON\s+(?:\w+\.)?(\w+)\s+TO\s+(\w+)",
    re.IGNORECASE,
)

_CONSTANT_RE: Final[re.Pattern[str]] = re.compile(
    r"(\w+)\s+CONSTANT\s+\w+\s*:=\s*([^;]+);", re.IGNORECASE
)

_PKG_VARIABLE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s+(\w+)\s+([\w%.]+(?:\s*%\s*(?:TYPE|ROWTYPE))?)\s*"
    r"(?::=\s*([^;]+))?\s*;",
    re.IGNORECASE | re.MULTILINE,
)

_INLINE_SQL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(SELECT\s+.+?\s+FROM\s+\w+.*?);",
    re.IGNORECASE | re.DOTALL,
)

_INSERT_SQL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(INSERT\s+INTO\s+\w+.*?);",
    re.IGNORECASE | re.DOTALL,
)

_UPDATE_SQL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(UPDATE\s+\w+\s+SET\s+.*?);",
    re.IGNORECASE | re.DOTALL,
)

_DELETE_SQL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(DELETE\s+FROM\s+\w+.*?);",
    re.IGNORECASE | re.DOTALL,
)

# PL/SQL keywords to exclude from variable detection
_PLSQL_KEYWORDS: Final[frozenset[str]] = frozenset({
    "BEGIN", "END", "IF", "THEN", "ELSE", "ELSIF", "LOOP", "WHILE",
    "FOR", "EXIT", "RETURN", "DECLARE", "EXCEPTION", "WHEN", "RAISE",
    "NULL", "OPEN", "CLOSE", "FETCH", "INTO", "CURSOR", "IS", "AS",
    "TYPE", "SUBTYPE", "PRAGMA", "EXECUTE", "IMMEDIATE", "GRANT",
    "CREATE", "OR", "REPLACE", "PACKAGE", "BODY", "PROCEDURE",
    "FUNCTION", "TRIGGER", "TABLE", "INDEX", "VIEW", "SEQUENCE",
    "IN", "OUT", "NOCOPY", "DEFAULT", "NOT", "AND", "LIKE",
})


def _find_autonomous_procs(content: str) -> list[str]:
    """Find procedures/functions that contain PRAGMA AUTONOMOUS_TRANSACTION.

    Returns:
        List of procedure/function names flagged as autonomous.
    """
    results: list[str] = []
    # Split on PROCEDURE/FUNCTION boundaries and check each for the pragma
    blocks = re.split(r"(?=\b(?:PROCEDURE|FUNCTION)\s+\w+)", content, flags=re.IGNORECASE)
    for block in blocks:
        if _PRAGMA_AUTONOMOUS_RE.search(block):
            m = re.match(r"(?:PROCEDURE|FUNCTION)\s+(\w+)", block, re.IGNORECASE)
            if m:
                results.append(m.group(1))
    return results


def _detect_ref_cursor_methods(content: str) -> list[str]:
    """Find functions/procedures that return or use SYS_REFCURSOR / REF CURSOR.

    Returns:
        List of method names that use REF CURSOR types.
    """
    results: list[str] = []
    blocks = re.split(r"(?=\b(?:PROCEDURE|FUNCTION)\s+\w+)", content, flags=re.IGNORECASE)
    for block in blocks:
        if _REF_CURSOR_RE.search(block):
            m = re.match(r"(?:PROCEDURE|FUNCTION)\s+(\w+)", block, re.IGNORECASE)
            if m:
                results.append(m.group(1))
    return results


def _is_in_package_spec(content: str) -> bool:
    """Check if the content represents a package specification (not body).

    Returns:
        True if this is a package spec, False otherwise.
    """
    return bool(
        re.search(r"PACKAGE\s+(?!BODY\b)\w+", content, re.IGNORECASE)
        and not re.search(r"PACKAGE\s+BODY\s+\w+", content, re.IGNORECASE)
    )


def extract(content: str, file_path: str) -> CodeStructure:
    """Extract deep structure from Oracle PL/SQL source code.

    Parses package specs/bodies, standalone procedures, functions, triggers,
    and various Oracle-specific patterns including DBMS_* usage, scheduler
    jobs, queue operations, TYPE definitions, and more.

    Args:
        content: Raw PL/SQL source code text.
        file_path: Relative or absolute file path for context.

    Returns:
        CodeStructure populated with extracted metadata mapped to the
        appropriate fields (methods, sql_queries, dependencies,
        entry_points, key_comments, hardcoded_values).
    """
    cs = CodeStructure(language="plsql", file_path=file_path)

    # ── Package name ──
    m = _PKG_NAME_RE.search(content)
    if m:
        cs.class_name = m.group(1)
        cs.package = m.group(1)

    # ── Procedures and functions ──
    seen_methods: set[str] = set()
    for m in _PROC_FUNC_RE.finditer(content):
        kind = m.group(1).upper()
        name = m.group(2)
        params = m.group(3).strip() if m.group(3) else ""
        return_type = m.group(4) or ""
        if name.upper() not in seen_methods:
            seen_methods.add(name.upper())
            cs.methods.append(MethodSignature(
                name=name,
                params=params,
                return_type=return_type,
                annotations=[kind],
            ))

    # ── PRAGMA AUTONOMOUS_TRANSACTION ──
    autonomous_procs = _find_autonomous_procs(content)
    for proc_name in autonomous_procs:
        cs.key_comments.append(
            f"AUTONOMOUS_TRANSACTION: {proc_name} commits independently (side effects)"
        )

    # ── BULK COLLECT / FORALL ──
    for m in _BULK_COLLECT_RE.finditer(content):
        cs.key_comments.append(f"BULK COLLECT INTO {m.group(1)} (performance-critical)")
    for m in _FORALL_RE.finditer(content):
        cs.key_comments.append(f"FORALL {m.group(1)} (bulk DML, performance-critical)")

    # ── REF CURSOR ──
    ref_cursor_methods = _detect_ref_cursor_methods(content)
    for method_name in ref_cursor_methods:
        # Update existing method annotation
        for ms in cs.methods:
            if ms.name.upper() == method_name.upper():
                ms.annotations.append("REF_CURSOR")
                break

    # ── TYPE definitions ──
    for m in _TYPE_TABLE_OF_RE.finditer(content):
        cs.key_comments.append(f"TYPE: {m.group(1)} IS TABLE OF {m.group(0).split('OF', 1)[1].strip()[:100]}")
    for m in _TYPE_RECORD_RE.finditer(content):
        cs.key_comments.append(f"TYPE: {m.group(1)} IS RECORD")
    for m in _TYPE_OBJECT_RE.finditer(content):
        cs.key_comments.append(f"TYPE: {m.group(1)} AS OBJECT")

    # ── Pipelined functions ──
    for m in _PIPELINED_RE.finditer(content):
        cs.key_comments.append(f"PIPELINED: {m.group(1)} (streaming result set)")

    # ── DETERMINISTIC / RESULT_CACHE ──
    for m in _DETERMINISTIC_RE.finditer(content):
        cs.key_comments.append(f"DETERMINISTIC: {m.group(1)} (same input = same output)")
    for m in _RESULT_CACHE_RE.finditer(content):
        cs.key_comments.append(f"RESULT_CACHE: {m.group(1)} (cached return value)")

    # ── Triggers ──
    # Check INSTEAD OF triggers first (more specific)
    instead_of_names: set[str] = set()
    for m in _INSTEAD_OF_TRIGGER_RE.finditer(content):
        trigger_name = m.group(1)
        operation = m.group(2)
        view_name = m.group(3)
        instead_of_names.add(trigger_name.upper())
        cs.entry_points.append(
            f"INSTEAD OF TRIGGER: {trigger_name} on {view_name} ({operation}) — contains business logic"
        )

    # Regular triggers (skip ones already captured as INSTEAD OF)
    for m in _TRIGGER_RE.finditer(content):
        trigger_name = m.group(1)
        if trigger_name.upper() not in instead_of_names:
            cs.entry_points.append(f"TRIGGER: {trigger_name}")

    # ── DBMS_SCHEDULER jobs ──
    for m in _SCHEDULER_JOB_NAME_RE.finditer(content):
        cs.entry_points.append(f"SCHEDULER JOB: {m.group(1)}")
    # Fallback if job_name not captured but call is present
    if not _SCHEDULER_JOB_NAME_RE.search(content):
        for m in _SCHEDULER_JOB_RE.finditer(content):
            cs.entry_points.append(f"SCHEDULER: {m.group(1)} call detected")

    # ── DBMS_AQ (Advanced Queuing) ──
    for m in _AQ_QUEUE_NAME_RE.finditer(content):
        cs.entry_points.append(f"AQ {m.group(0).split('(')[0].split('.')[-1].strip()}: queue {m.group(1)}")
    if not _AQ_QUEUE_NAME_RE.search(content):
        for m in _AQ_RE.finditer(content):
            cs.entry_points.append(f"AQ: {m.group(1)} operation detected")

    # ── UTL_FILE operations ──
    utl_file_ops: list[str] = []
    for m in _UTL_FILE_OPS_RE.finditer(content):
        utl_file_ops.append(m.group(1).upper())
    if utl_file_ops:
        unique_ops = sorted(set(utl_file_ops))
        cs.dependencies.append(f"UTL_FILE ({', '.join(unique_ops)})")

    # ── DBMS_* and UTL_* package dependencies ──
    dbms_deps: set[str] = set()
    for m in _DBMS_PKG_RE.finditer(content):
        dbms_deps.add(m.group(1).upper())
    for m in _UTL_PKG_RE.finditer(content):
        pkg = m.group(1).upper()
        # UTL_FILE is already captured with operations above
        if pkg != "UTL_FILE":
            dbms_deps.add(pkg)
    cs.dependencies.extend(sorted(dbms_deps))

    # ── %TYPE / %ROWTYPE references → table dependencies ──
    type_tables: set[str] = set()
    for m in _TYPE_ROWTYPE_RE.finditer(content):
        table_name = m.group(1).upper()
        type_tables.add(table_name)
        cs.dependencies.append(f"TABLE: {m.group(1)}")
    # Deduplicate dependencies
    cs.dependencies = list(dict.fromkeys(cs.dependencies))

    # ── Cursor declarations with SELECT ──
    for m in _CURSOR_RE.finditer(content):
        cursor_name = m.group(1)
        cursor_sql = m.group(2).strip()
        # Normalize whitespace
        cursor_sql = re.sub(r"\s+", " ", cursor_sql)[:300]
        cs.sql_queries.append(f"CURSOR {cursor_name}: {cursor_sql}")

    # ── Dynamic SQL (EXECUTE IMMEDIATE) ──
    for m in _EXECUTE_IMMEDIATE_RE.finditer(content):
        sql_text = m.group(1).strip()
        sql_text = re.sub(r"\s+", " ", sql_text)[:300]
        cs.sql_queries.append(f"[DYNAMIC] EXECUTE IMMEDIATE {sql_text}")

    # ── Inline SQL (SELECT, INSERT, UPDATE, DELETE not in cursors) ──
    for pattern in (_INSERT_SQL_RE, _UPDATE_SQL_RE, _DELETE_SQL_RE):
        for m in pattern.finditer(content):
            sql_text = re.sub(r"\s+", " ", m.group(1).strip())[:300]
            # Avoid duplicating cursor SELECTs
            if not any(sql_text[:50] in existing for existing in cs.sql_queries):
                cs.sql_queries.append(sql_text)
                if len(cs.sql_queries) >= 50:
                    break

    # ── Global temporary tables ──
    for m in _GTT_RE.finditer(content):
        cs.key_comments.append(
            f"GLOBAL TEMPORARY TABLE: {m.group(1)} (ON COMMIT {m.group(2).upper()} ROWS)"
        )

    # ── GRANT statements ──
    for m in _GRANT_RE.finditer(content):
        privileges = m.group(1).strip()
        obj_name = m.group(2)
        grantee = m.group(3)
        cs.key_comments.append(f"GRANT {privileges} ON {obj_name} TO {grantee}")

    # ── Exception handlers ──
    seen_exceptions: set[str] = set()
    for m in _EXCEPTION_RE.finditer(content):
        exc_name = m.group(1).upper()
        if exc_name not in seen_exceptions:
            seen_exceptions.add(exc_name)
            cs.key_comments.append(f"Exception handler: {exc_name}")

    # ── Package-level constants ──
    for m in _CONSTANT_RE.finditer(content):
        const_name = m.group(1)
        const_value = m.group(2).strip()[:100]
        if const_name.upper() not in _PLSQL_KEYWORDS:
            cs.hardcoded_values.append(HardcodedValue(
                name=const_name,
                value=const_value,
                line_hint="CONSTANT",
            ))

    # ── Package-level variables (in package spec) ──
    if _is_in_package_spec(content):
        # Extract spec section to find global variables
        spec_match = re.search(
            r"PACKAGE\s+(?!BODY\b)\w+\s+(?:IS|AS)\b(.*?)END\s+\w+\s*;",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if spec_match:
            spec_body = spec_match.group(1)
            for m in _PKG_VARIABLE_RE.finditer(spec_body):
                var_name = m.group(1)
                var_type = m.group(2)
                var_init = m.group(3)
                if var_name.upper() not in _PLSQL_KEYWORDS and not re.match(
                    r"(?:PROCEDURE|FUNCTION|CURSOR|TYPE|SUBTYPE|PRAGMA)\b",
                    var_name,
                    re.IGNORECASE,
                ):
                    value = f"{var_type}"
                    if var_init:
                        value += f" := {var_init.strip()[:50]}"
                    cs.key_comments.append(f"PACKAGE VARIABLE: {var_name} {value}")

    # ── Key comments (TODO, FIXME, BUSINESS RULE) ──
    for m in re.finditer(
        r"--\s*(TODO|FIXME|HACK|XXX|IMPORTANT|BUSINESS\s*RULE)[:\s]*(.*)",
        content,
        re.IGNORECASE,
    ):
        cs.key_comments.append(f"{m.group(1).upper()}: {m.group(2).strip()}"[:200])

    return cs
