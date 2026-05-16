"""Deep COBOL / CICS / DB2 code structure extractor.

Extracts enterprise COBOL patterns including:
- WORKING-STORAGE fields with PIC clause analysis and REDEFINES
- LINKAGE SECTION (API contract / parameters)
- PROCEDURE DIVISION USING (function signature)
- EVALUATE/WHEN business rules
- 88-level conditions with parent context
- File I/O operations (OPEN, READ, WRITE, REWRITE, DELETE, CLOSE)
- SORT/MERGE statements
- PERFORM VARYING loops
- STRING/UNSTRING transformations
- COMPUTE formulas
- Enhanced CICS: TRANSID, COMMAREA, MAP/MAPSET, LINK/XCTL
- Enhanced DB2: table names, INCLUDE, DECLARE CURSOR, WHENEVER
- COPY REPLACING
- Nested programs
- DECLARATIVES sections

Uses only regex. Handles both fixed-format (cols 7-72) and free-format COBOL.
"""

import logging
import re

from src.agents.ingest.skills.code_structure_skill import (
    CodeStructure,
    HardcodedValue,
    MethodSignature,
)

logger = logging.getLogger(__name__)


def _strip_cobol_line_numbers(content: str) -> str:
    """Strip sequence numbers (cols 1-6) from fixed-format COBOL.

    Returns content with only the significant portion (cols 7-72+).
    Also removes comment lines (indicator '*' or '/' in col 7).
    """
    lines: list[str] = []
    for line in content.splitlines():
        if len(line) >= 7:
            indicator = line[6]
            if indicator in ("*", "/"):
                # Comment line -- keep for key_comments extraction later
                lines.append(f"*{line[7:]}")
                continue
            if indicator == "-":
                # Continuation line
                lines.append(f"-{line[7:]}")
                continue
            # Strip sequence area (cols 1-6), keep code area
            lines.append(line[6:])
        else:
            lines.append(line)
    return "\n".join(lines)


def _describe_pic(pic: str) -> str:
    """Describe a PIC clause as numeric or alphanumeric.

    Args:
        pic: The PIC clause string, e.g. '9(5)V9(2)', 'X(10)', 'S9(7)V99'.

    Returns:
        Human-readable type description.
    """
    pic_upper = pic.upper().strip()
    if re.search(r"[9SVPZ]", pic_upper) and not re.search(r"X", pic_upper):
        if "V" in pic_upper or re.search(r"V9", pic_upper):
            return "numeric (decimal)"
        if pic_upper.startswith("S"):
            return "numeric (signed)"
        return "numeric"
    if re.search(r"X", pic_upper):
        return "alphanumeric"
    return "unknown"


def _extract_program_id(content: str, cs: CodeStructure) -> None:
    """Extract PROGRAM-ID."""
    m = re.search(r"PROGRAM-ID\.\s*(\S+)", content, re.IGNORECASE)
    if m:
        cs.class_name = m.group(1).rstrip(".")


def _extract_copy_statements(content: str, cs: CodeStructure) -> None:
    """Extract COPY statements including REPLACING clauses."""
    for m in re.finditer(
        r"COPY\s+(\S+?)\.?"
        r"(?:\s+REPLACING\s+(.*?))?\s*\.",
        content,
        re.IGNORECASE | re.DOTALL,
    ):
        copybook = m.group(1).rstrip(".")
        replacing = m.group(2)
        if replacing:
            replacing_clean = " ".join(replacing.split())[:150]
            cs.imports.append(f"{copybook} REPLACING {replacing_clean}")
        else:
            cs.imports.append(copybook)


def _extract_working_storage(content: str, cs: CodeStructure) -> None:
    """Extract WORKING-STORAGE 01-level records with PIC clauses and REDEFINES.

    Tracks parent fields for 88-level context.
    """
    # Match level numbers with field names and PIC clauses
    field_pattern = re.compile(
        r"^\s*(\d{2})\s+([\w-]+)"
        r"(?:\s+REDEFINES\s+([\w-]+))?"
        r"(?:.*?PIC(?:TURE)?\s+IS\s+([\w(). SVX9+-]+)|.*?PIC(?:TURE)?\s+([\w(). SVX9+-]+))?"
        r"(?:.*?VALUE\s+(?:IS\s+)?(.*?))?"
        r"\s*\.",
        re.IGNORECASE | re.MULTILINE,
    )

    ws_section = _get_section(content, "WORKING-STORAGE SECTION")
    if not ws_section:
        return

    current_parent: str = ""
    current_parent_pic: str = ""

    for m in field_pattern.finditer(ws_section):
        level = m.group(1)
        name = m.group(2)
        redefines = m.group(3)
        pic = m.group(4) or m.group(5) or ""
        value = m.group(6)

        if name.upper() == "FILLER":
            continue

        level_num = int(level)

        # Track 01-level records
        if level_num == 1:
            pic_desc = _describe_pic(pic) if pic else "group"
            desc = "01-level record"
            if pic:
                desc += f" PIC {pic.strip()} ({pic_desc})"
            if redefines:
                desc += f" REDEFINES {redefines}"
            cs.hardcoded_values.append(HardcodedValue(
                name=name,
                value=desc,
                line_hint="WORKING-STORAGE",
            ))

        # Track parent field for 88-level context
        if level_num < 88:
            current_parent = name
            current_parent_pic = pic.strip() if pic else ""

        # 88-level conditions with parent context
        if level_num == 88 and value:
            parent_info = current_parent
            if current_parent_pic:
                pic_type = _describe_pic(current_parent_pic)
                parent_info += f" (PIC {current_parent_pic}, {pic_type})"
            value_clean = value.strip().rstrip(".")[:100]
            cs.key_comments.append(
                f"BUSINESS RULE: {parent_info}: {name} = {value_clean}"
            )

        # Track REDEFINES relationships
        if redefines and level_num != 1:
            cs.key_comments.append(
                f"REDEFINES: {name} REDEFINES {redefines}"
                + (f" PIC {pic.strip()}" if pic else "")
            )

        # Hardcoded values from VALUE clauses (non-88)
        if value and level_num != 88:
            val_clean = value.strip().rstrip(".")
            if val_clean and val_clean.upper() not in ("SPACES", "ZEROS", "ZEROES", "LOW-VALUES", "HIGH-VALUES"):
                cs.hardcoded_values.append(HardcodedValue(
                    name=name,
                    value=val_clean[:100],
                    line_hint=f"Level {level}",
                ))


def _extract_linkage_section(content: str, cs: CodeStructure) -> None:
    """Extract LINKAGE SECTION fields -- the API contract."""
    linkage = _get_section(content, "LINKAGE SECTION")
    if not linkage:
        return

    field_pattern = re.compile(
        r"^\s*(\d{2})\s+([\w-]+)"
        r"(?:.*?PIC(?:TURE)?\s+(?:IS\s+)?([\w(). SVX9+-]+))?"
        r"\s*\.",
        re.IGNORECASE | re.MULTILINE,
    )

    linkage_fields: list[str] = []
    for m in field_pattern.finditer(linkage):
        level = m.group(1)
        name = m.group(2)
        pic = m.group(3)

        if name.upper() == "FILLER":
            continue

        desc = f"LINKAGE {level} {name}"
        if pic:
            pic_type = _describe_pic(pic)
            desc += f" PIC {pic.strip()} ({pic_type})"
        linkage_fields.append(desc)

    if linkage_fields:
        cs.key_comments.append(
            f"API CONTRACT (LINKAGE SECTION): {'; '.join(linkage_fields[:20])}"
        )


def _extract_procedure_division_using(content: str, cs: CodeStructure) -> None:
    """Extract PROCEDURE DIVISION USING parameter list (function signature)."""
    m = re.search(
        r"PROCEDURE\s+DIVISION\s+USING\s+(.*?)\.+",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        params_raw = m.group(1).strip()
        params = " ".join(params_raw.split())
        cs.entry_points.append(f"PROCEDURE DIVISION USING {params}")


def _extract_paragraphs_and_sections(content: str, cs: CodeStructure) -> None:
    """Extract PROCEDURE DIVISION paragraphs and sections (methods)."""
    proc_div = _get_section(content, "PROCEDURE DIVISION")
    if not proc_div:
        return

    # Section headers: NAME SECTION.
    for m in re.finditer(r"^\s{0,11}([\w][\w-]+)\s+SECTION\s*\.", proc_div, re.MULTILINE | re.IGNORECASE):
        name = m.group(1)
        if name.upper() not in ("PROCEDURE", "DECLARATIVES"):
            cs.methods.append(MethodSignature(name=f"{name} SECTION"))

    # Paragraph headers: NAME. (at proper column, not keywords)
    skip_keywords = {
        "DIVISION", "SECTION", "PROGRAM-ID", "FD", "SD", "COPY",
        "PERFORM", "MOVE", "IF", "ELSE", "END-IF", "ADD", "SUBTRACT",
        "MULTIPLY", "DIVIDE", "COMPUTE", "EVALUATE", "WHEN", "CALL",
        "DISPLAY", "ACCEPT", "READ", "WRITE", "OPEN", "CLOSE",
        "GO", "STOP", "EXIT", "STRING", "UNSTRING", "INSPECT",
        "INITIALIZE", "SET", "SORT", "MERGE", "SEARCH",
        "REWRITE", "DELETE", "RETURN", "RELEASE", "START",
    }
    for m in re.finditer(r"^\s{7,11}([\w][\w-]+)\s*\.\s*$", proc_div, re.MULTILINE):
        name = m.group(1)
        if name.upper() not in skip_keywords and not any(
            kw in name.upper() for kw in ("DIVISION", "SECTION")
        ):
            cs.methods.append(MethodSignature(name=name))


def _extract_evaluate_blocks(content: str, cs: CodeStructure) -> None:
    """Extract EVALUATE/WHEN blocks as business rules."""
    eval_pattern = re.compile(
        r"EVALUATE\s+(.*?)\s*\n(.*?)END-EVALUATE",
        re.IGNORECASE | re.DOTALL,
    )
    for m in eval_pattern.finditer(content):
        subject = m.group(1).strip()
        body = m.group(2).strip()

        # Extract WHEN conditions
        when_clauses: list[str] = []
        for wm in re.finditer(r"WHEN\s+(.*?)(?=\s+WHEN\s|\s+END-EVALUATE|\Z)", body, re.IGNORECASE | re.DOTALL):
            clause = " ".join(wm.group(1).split())[:100]
            when_clauses.append(clause)

        rule_text = f"EVALUATE {' '.join(subject.split())}"
        if when_clauses:
            rule_text += " | " + " | ".join(f"WHEN {w}" for w in when_clauses[:10])

        cs.key_comments.append(f"BUSINESS RULE: {rule_text[:500]}")


def _extract_file_io(content: str, cs: CodeStructure) -> None:
    """Extract file I/O operations: OPEN, READ, WRITE, REWRITE, DELETE, CLOSE.

    Also track SELECT ... ASSIGN TO and FD entries.
    """
    # SELECT ... ASSIGN TO
    for m in re.finditer(
        r"SELECT\s+([\w-]+)\s+ASSIGN\s+TO\s+([\w-]+)",
        content,
        re.IGNORECASE,
    ):
        cs.dependencies.append(f"FILE: {m.group(1)} ASSIGN {m.group(2)}")

    # FD (file descriptors)
    for m in re.finditer(r"FD\s+([\w-]+)", content, re.IGNORECASE):
        fd_name = m.group(1).rstrip(".")
        if f"FILE: {fd_name}" not in cs.dependencies:
            cs.dependencies.append(f"FILE: {fd_name}")

    # OPEN statements with mode
    for m in re.finditer(
        r"OPEN\s+(INPUT|OUTPUT|I-O|EXTEND)\s+([\w-]+(?:\s+[\w-]+)*)",
        content,
        re.IGNORECASE,
    ):
        mode = m.group(1).upper()
        files = re.findall(r"[\w-]+", m.group(2))
        for f in files:
            cs.key_comments.append(f"FILE I/O: OPEN {mode} {f}")

    # READ, WRITE, REWRITE, DELETE, CLOSE
    for op in ("READ", "WRITE", "REWRITE", "DELETE", "CLOSE"):
        for m in re.finditer(rf"{op}\s+([\w-]+)", content, re.IGNORECASE):
            fname = m.group(1)
            if fname.upper() not in ("FROM", "INTO", "END-READ", "END-WRITE",
                                      "END-REWRITE", "END-DELETE", "RECORD",
                                      "AT", "WITH", "INVALID", "NOT"):
                cs.key_comments.append(f"FILE I/O: {op} {fname}")


def _extract_sort_merge(content: str, cs: CodeStructure) -> None:
    """Extract SORT/MERGE statements with keys and files."""
    sort_pattern = re.compile(
        r"(SORT|MERGE)\s+([\w-]+)\s+(?:ON\s+)?(.*?)(?:USING|GIVING|INPUT|OUTPUT)\s+(.*?)(?:\.\s|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in sort_pattern.finditer(content):
        op = m.group(1).upper()
        sort_file = m.group(2)
        keys_part = " ".join(m.group(3).split())[:100]
        files_part = " ".join(m.group(4).split())[:100]
        cs.key_comments.append(f"{op}: {sort_file} {keys_part} {files_part}".strip())


def _extract_perform_varying(content: str, cs: CodeStructure) -> None:
    """Extract PERFORM VARYING loops -- often contain business-significant ranges."""
    vary_pattern = re.compile(
        r"PERFORM\s+([\w-]+)\s+VARYING\s+([\w-]+)\s+FROM\s+(\S+)\s+BY\s+(\S+)\s+UNTIL\s+(.*?)(?:\s+END-PERFORM|\s*\.)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in vary_pattern.finditer(content):
        para = m.group(1)
        var = m.group(2)
        frm = m.group(3)
        by = m.group(4)
        until = " ".join(m.group(5).split())[:80]
        cs.key_comments.append(
            f"LOOP: PERFORM {para} VARYING {var} FROM {frm} BY {by} UNTIL {until}"
        )


def _extract_string_unstring(content: str, cs: CodeStructure) -> None:
    """Extract STRING/UNSTRING data transformation operations."""
    for op in ("STRING", "UNSTRING"):
        pattern = re.compile(
            rf"{op}\s+(.*?)(?:END-{op}|\.\s)",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pattern.finditer(content):
            body = " ".join(m.group(1).split())[:200]
            # Extract INTO/DELIMITED BY fields
            into_match = re.search(r"INTO\s+([\w-]+)", body, re.IGNORECASE)
            dest = into_match.group(1) if into_match else "?"
            cs.key_comments.append(f"DATA TRANSFORM: {op} -> {dest}: {body[:150]}")


def _extract_compute(content: str, cs: CodeStructure) -> None:
    """Extract COMPUTE expressions -- often business formulas."""
    compute_pattern = re.compile(
        r"COMPUTE\s+([\w-]+)\s*=\s*(.*?)(?:END-COMPUTE|\.\s|\.\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in compute_pattern.finditer(content):
        target = m.group(1)
        expr = " ".join(m.group(2).split())[:200]
        cs.key_comments.append(f"BUSINESS RULE: COMPUTE {target} = {expr}")


def _extract_cics_enhanced(content: str, cs: CodeStructure) -> None:
    """Extract enhanced CICS patterns.

    - TRANSID from RECEIVE/SEND
    - COMMAREA structure
    - MAP/MAPSET names
    - PROGRAM names from LINK/XCTL
    """
    cics_pattern = re.compile(
        r"EXEC\s+CICS\s+(\w+)(.*?)END-EXEC",
        re.IGNORECASE | re.DOTALL,
    )
    for m in cics_pattern.finditer(content):
        command = m.group(1).upper()
        body = m.group(2)

        cs.entry_points.append(f"CICS {command}")

        # TRANSID
        transid_match = re.search(r"TRANSID\s*\(\s*['\"]?(\w+)", body, re.IGNORECASE)
        if transid_match:
            cs.entry_points.append(f"CICS TRANSID {transid_match.group(1)}")

        # COMMAREA
        commarea_match = re.search(r"COMMAREA\s*\(\s*([\w-]+)", body, re.IGNORECASE)
        if commarea_match:
            cs.entry_points.append(f"CICS COMMAREA {commarea_match.group(1)}")

        # MAP / MAPSET
        map_match = re.search(r"MAP\s*\(\s*['\"]?(\w+)", body, re.IGNORECASE)
        mapset_match = re.search(r"MAPSET\s*\(\s*['\"]?(\w+)", body, re.IGNORECASE)
        if map_match:
            map_name = map_match.group(1)
            mapset_name = mapset_match.group(1) if mapset_match else ""
            entry = f"CICS MAP {map_name}"
            if mapset_name:
                entry += f" MAPSET {mapset_name}"
            cs.entry_points.append(entry)

        # PROGRAM from LINK / XCTL
        if command in ("LINK", "XCTL"):
            prog_match = re.search(r"PROGRAM\s*\(\s*['\"]?(\w+)", body, re.IGNORECASE)
            if prog_match:
                cs.entry_points.append(f"CICS {command} PROGRAM {prog_match.group(1)}")
                cs.dependencies.append(f"CALL: {prog_match.group(1)}")


def _extract_db2_enhanced(content: str, cs: CodeStructure) -> None:
    """Extract enhanced DB2 / embedded SQL patterns.

    - Table names from SELECT/INSERT/UPDATE/DELETE
    - INCLUDE SQLCA/SQLDA
    - DECLARE CURSOR names
    - WHENEVER conditions
    """
    sql_pattern = re.compile(
        r"EXEC\s+SQL(.*?)END-EXEC",
        re.IGNORECASE | re.DOTALL,
    )
    for m in sql_pattern.finditer(content):
        sql_body = m.group(1).strip()
        sql_clean = " ".join(sql_body.split())[:300]
        cs.sql_queries.append(sql_clean)

        # Extract table names from DML
        # SELECT ... FROM table
        for tm in re.finditer(r"FROM\s+([\w.]+)", sql_body, re.IGNORECASE):
            table = tm.group(1)
            if table.upper() not in ("DUAL", "SYSIBM"):
                cs.dependencies.append(f"TABLE: {table}")

        # INSERT INTO table
        for tm in re.finditer(r"INSERT\s+INTO\s+([\w.]+)", sql_body, re.IGNORECASE):
            cs.dependencies.append(f"TABLE: {tm.group(1)}")

        # UPDATE table
        for tm in re.finditer(r"UPDATE\s+([\w.]+)", sql_body, re.IGNORECASE):
            cs.dependencies.append(f"TABLE: {tm.group(1)}")

        # DELETE FROM table
        for tm in re.finditer(r"DELETE\s+FROM\s+([\w.]+)", sql_body, re.IGNORECASE):
            cs.dependencies.append(f"TABLE: {tm.group(1)}")

        # JOIN table
        for tm in re.finditer(r"JOIN\s+([\w.]+)", sql_body, re.IGNORECASE):
            cs.dependencies.append(f"TABLE: {tm.group(1)}")

        # INCLUDE SQLCA / SQLDA
        include_match = re.search(r"INCLUDE\s+(SQLCA|SQLDA|[\w]+)", sql_body, re.IGNORECASE)
        if include_match:
            cs.imports.append(f"SQL INCLUDE {include_match.group(1)}")

        # DECLARE cursor
        cursor_match = re.search(r"DECLARE\s+([\w-]+)\s+CURSOR", sql_body, re.IGNORECASE)
        if cursor_match:
            cs.entry_points.append(f"DB2 CURSOR {cursor_match.group(1)}")

        # WHENEVER condition
        whenever_match = re.search(
            r"WHENEVER\s+(SQLERROR|SQLWARNING|NOT\s+FOUND)\s+(.*?)$",
            sql_body,
            re.IGNORECASE | re.MULTILINE,
        )
        if whenever_match:
            cs.key_comments.append(
                f"DB2 ERROR HANDLING: WHENEVER {whenever_match.group(1)} "
                f"{whenever_match.group(2).strip()[:80]}"
            )


def _extract_call_targets(content: str, cs: CodeStructure) -> None:
    """Extract CALL statement targets (program dependencies)."""
    for m in re.finditer(r"CALL\s+['\"](\w+)['\"]", content, re.IGNORECASE):
        dep = m.group(1)
        if dep not in cs.dependencies and f"CALL: {dep}" not in cs.dependencies:
            cs.dependencies.append(dep)

    # Dynamic CALL (variable name)
    for m in re.finditer(r"CALL\s+([\w-]+)(?:\s+USING)?", content, re.IGNORECASE):
        target = m.group(1)
        if target.upper() not in ("USING", "BY", "CONTENT", "REFERENCE", "VALUE"):
            dep = f"DYNAMIC CALL: {target}"
            if dep not in cs.dependencies:
                cs.dependencies.append(dep)


def _extract_nested_programs(content: str, cs: CodeStructure) -> None:
    """Detect nested programs (multiple PROGRAM-ID within one file)."""
    program_ids = re.findall(r"PROGRAM-ID\.\s*(\S+)", content, re.IGNORECASE)
    program_ids = [p.rstrip(".") for p in program_ids]
    if len(program_ids) > 1:
        for pid in program_ids[1:]:
            cs.key_comments.append(f"NESTED PROGRAM: {pid}")
            cs.entry_points.append(f"NESTED PROGRAM-ID {pid}")


def _extract_declaratives(content: str, cs: CodeStructure) -> None:
    """Extract DECLARATIVES error handling sections."""
    decl_match = re.search(
        r"DECLARATIVES\s*\.(.*?)END\s+DECLARATIVES\s*\.",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    if not decl_match:
        return

    decl_body = decl_match.group(1)

    # Extract SECTION names and USE statements
    for m in re.finditer(
        r"([\w-]+)\s+SECTION\s*\..*?USE\s+(.*?)\.",
        decl_body,
        re.IGNORECASE | re.DOTALL,
    ):
        section_name = m.group(1)
        use_clause = " ".join(m.group(2).split())[:100]
        cs.key_comments.append(f"DECLARATIVE: {section_name} SECTION USE {use_clause}")


def _extract_key_comments(content: str, cs: CodeStructure) -> None:
    """Extract significant comments from COBOL source.

    COBOL comments have '*' in column 7 (fixed-format) or '*>' anywhere (free-format).
    """
    comment_patterns = [
        # Fixed-format comment lines (already converted to *... by _strip_cobol_line_numbers)
        re.compile(r"^\*\s*(TODO|FIXME|HACK|XXX|BUSINESS\s*RULE|IMPORTANT)[:\s]*(.*)", re.IGNORECASE | re.MULTILINE),
        # Free-format inline comments
        re.compile(r"\*>\s*(TODO|FIXME|HACK|XXX|BUSINESS\s*RULE|IMPORTANT)[:\s]*(.*)", re.IGNORECASE),
    ]
    for pattern in comment_patterns:
        for m in pattern.finditer(content):
            comment = f"{m.group(1).strip()}: {m.group(2).strip()}"[:200]
            if comment not in cs.key_comments:
                cs.key_comments.append(comment)


def _extract_hardcoded_literals(content: str, cs: CodeStructure) -> None:
    """Extract hardcoded literal values from IF/EVALUATE conditions."""
    # IF field = 'literal'
    for m in re.finditer(
        r"IF\s+([\w-]+)\s*=\s*['\"]([^'\"]+)['\"]",
        content,
        re.IGNORECASE,
    ):
        cs.hardcoded_values.append(HardcodedValue(
            name=m.group(1),
            value=f"'{m.group(2)}'",
            line_hint="IF condition",
        ))

    # WHEN 'literal' or WHEN numeric
    for m in re.finditer(
        r"WHEN\s+['\"]([^'\"]+)['\"]",
        content,
        re.IGNORECASE,
    ):
        cs.hardcoded_values.append(HardcodedValue(
            name="EVALUATE/WHEN",
            value=f"'{m.group(1)}'",
            line_hint="EVALUATE condition",
        ))

    # MOVE literal TO field
    for m in re.finditer(
        r"MOVE\s+(\d{3,}|['\"][^'\"]{2,50}['\"])\s+TO\s+([\w-]+)",
        content,
        re.IGNORECASE,
    ):
        cs.hardcoded_values.append(HardcodedValue(
            name=m.group(2),
            value=m.group(1),
            line_hint="MOVE literal",
        ))


def _get_section(content: str, section_name: str) -> str:
    """Extract the text of a named COBOL section/division.

    Args:
        content: Full COBOL source.
        section_name: e.g. 'WORKING-STORAGE SECTION', 'LINKAGE SECTION'.

    Returns:
        The section text, or empty string if not found.
    """
    # Find section start
    pattern = re.compile(
        rf"{re.escape(section_name)}\s*\.",
        re.IGNORECASE,
    )
    start_match = pattern.search(content)
    if not start_match:
        return ""

    start = start_match.end()

    # Find next section/division boundary
    next_section = re.compile(
        r"(?:WORKING-STORAGE|LINKAGE|LOCAL-STORAGE|FILE|COMMUNICATION|REPORT|SCREEN)"
        r"\s+SECTION\s*\."
        r"|(?:PROCEDURE|DATA|ENVIRONMENT|IDENTIFICATION)\s+DIVISION",
        re.IGNORECASE,
    )
    end_match = next_section.search(content, start)
    end = end_match.start() if end_match else len(content)

    return content[start:end]


def _deduplicate_list(items: list[str]) -> list[str]:
    """Deduplicate a list while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract(content: str, file_path: str) -> CodeStructure:
    """Deep COBOL/CICS/DB2 code structure extraction.

    Extracts enterprise COBOL patterns including working storage, linkage section,
    procedure division parameters, EVALUATE business rules, 88-level conditions,
    file I/O, SORT/MERGE, PERFORM VARYING, STRING/UNSTRING, COMPUTE formulas,
    CICS commands, DB2 embedded SQL, COPY REPLACING, nested programs, and
    DECLARATIVES error handling.

    Args:
        content: Raw COBOL source code text.
        file_path: File path for context in the output.

    Returns:
        CodeStructure populated with extracted COBOL metadata.
    """
    cs = CodeStructure(language="cobol", file_path=file_path)

    # Extract program identity first
    _extract_program_id(content, cs)

    # COPY/REPLACING (before stripping, as format matters)
    _extract_copy_statements(content, cs)

    # WORKING-STORAGE fields, 88-levels with parent context
    _extract_working_storage(content, cs)

    # LINKAGE SECTION (API contract)
    _extract_linkage_section(content, cs)

    # PROCEDURE DIVISION USING (function signature)
    _extract_procedure_division_using(content, cs)

    # Paragraphs and sections (methods)
    _extract_paragraphs_and_sections(content, cs)

    # EVALUATE/WHEN business rules
    _extract_evaluate_blocks(content, cs)

    # File I/O operations
    _extract_file_io(content, cs)

    # SORT/MERGE
    _extract_sort_merge(content, cs)

    # PERFORM VARYING loops
    _extract_perform_varying(content, cs)

    # STRING/UNSTRING transformations
    _extract_string_unstring(content, cs)

    # COMPUTE formulas
    _extract_compute(content, cs)

    # Enhanced CICS
    _extract_cics_enhanced(content, cs)

    # Enhanced DB2 / embedded SQL
    _extract_db2_enhanced(content, cs)

    # CALL targets
    _extract_call_targets(content, cs)

    # Nested programs
    _extract_nested_programs(content, cs)

    # DECLARATIVES
    _extract_declaratives(content, cs)

    # Key comments
    _extract_key_comments(content, cs)

    # Hardcoded literals in conditions
    _extract_hardcoded_literals(content, cs)

    # Deduplicate lists
    cs.imports = _deduplicate_list(cs.imports)
    cs.dependencies = _deduplicate_list(cs.dependencies)
    cs.entry_points = _deduplicate_list(cs.entry_points)
    cs.key_comments = _deduplicate_list(cs.key_comments)

    return cs
