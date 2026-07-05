"""Deep Progress 4GL / OpenEdge ABL code structure extractor.

Extracts procedures, functions, temp-tables, buffers, queries,
transactions, datasets, AppServer calls, and event patterns.
"""

from __future__ import annotations

import logging
import re

from src.agents.ingest.skills.code_structure_skill import (
    CodeStructure,
    HardcodedValue,
    MethodSignature,
)

logger = logging.getLogger(__name__)


def extract(content: str, file_path: str) -> CodeStructure:
    """Extract structure from Progress 4GL / OpenEdge ABL source."""
    cs = CodeStructure(language="progress_4gl", file_path=file_path)

    # ─── Class (if .cls) ───
    m = re.search(r"CLASS\s+([\w.]+)(?:\s+INHERITS\s+([\w.]+))?", content, re.IGNORECASE)
    if m:
        cs.class_name = m.group(1)
        cs.package = ".".join(m.group(1).split(".")[:-1])
        if m.group(2):
            cs.parent_class = m.group(2)

    # Implements
    for m in re.finditer(r"IMPLEMENTS\s+([\w.]+)", content, re.IGNORECASE):
        cs.interfaces.append(m.group(1))

    # ─── Procedures ───
    for m in re.finditer(r"PROCEDURE\s+([\w-]+)\s*:", content, re.IGNORECASE):
        cs.methods.append(MethodSignature(name=m.group(1)))

    # ─── Functions with return types ───
    for m in re.finditer(
        r"FUNCTION\s+([\w-]+)\s+RETURNS\s+(\w+)",
        content, re.IGNORECASE,
    ):
        cs.methods.append(MethodSignature(name=m.group(1), return_type=m.group(2)))

    # ─── DEFINE TEMP-TABLE (entity definitions) ───
    for m in re.finditer(
        r"DEFINE\s+(?:NEW\s+)?(?:SHARED\s+)?TEMP-TABLE\s+([\w-]+)",
        content, re.IGNORECASE,
    ):
        cs.key_comments.append(f"TEMP-TABLE: {m.group(1)}")

    # Temp-table fields
    for m in re.finditer(
        r"DEFINE\s+(?:NEW\s+)?(?:SHARED\s+)?TEMP-TABLE\s+([\w-]+)(.*?)(?:INDEX|\.)",
        content, re.IGNORECASE | re.DOTALL,
    ):
        table_name = m.group(1)
        body = m.group(2)
        fields = re.findall(r"FIELD\s+([\w-]+)\s+AS\s+(\w+)", body, re.IGNORECASE)
        if fields:
            field_list = ", ".join(f"{n} ({t})" for n, t in fields[:10])
            cs.key_comments.append(f"TEMP-TABLE {table_name} fields: {field_list}")

    # ─── DEFINE BUFFER (separate DB access scope) ───
    for m in re.finditer(r"DEFINE\s+BUFFER\s+([\w-]+)\s+FOR\s+([\w-]+)", content, re.IGNORECASE):
        cs.dependencies.append(f"BUFFER: {m.group(1)} FOR {m.group(2)}")

    # ─── FOR EACH queries (DB access) ───
    for m in re.finditer(
        r"FOR\s+EACH\s+([\w-]+)(?:\s+(?:OF\s+[\w-]+\s+)?WHERE\s+([^:]+?))?(?:\s+NO-LOCK|\s+EXCLUSIVE-LOCK|\s+SHARE-LOCK)?(?:\s*:|\s*,)",
        content, re.IGNORECASE,
    ):
        query = f"FOR EACH {m.group(1)}"
        if m.group(2):
            query += f" WHERE {m.group(2).strip()[:150]}"
        cs.sql_queries.append(query)

    # ─── FIND statements ───
    for m in re.finditer(
        r"FIND\s+(?:FIRST|LAST)?\s*([\w-]+)(?:\s+WHERE\s+([^.]+?))?(?:\s+NO-LOCK|\s+NO-ERROR)?",
        content, re.IGNORECASE,
    ):
        query = f"FIND {m.group(1)}"
        if m.group(2):
            query += f" WHERE {m.group(2).strip()[:100]}"
        cs.sql_queries.append(query)

    # ─── CAN-FIND (existence check without lock) ───
    for m in re.finditer(r"CAN-FIND\s*\(\s*([\w-]+)(?:\s+WHERE\s+([^)]+))?\)", content, re.IGNORECASE):
        cs.key_comments.append(f"VALIDATION: CAN-FIND {m.group(1)}" + (f" WHERE {m.group(2).strip()[:80]}" if m.group(2) else ""))

    # ─── RUN dependencies ───
    for m in re.finditer(r"RUN\s+([\w/.-]+)(?:\s+PERSISTENT)?", content, re.IGNORECASE):
        target = m.group(1)
        if "PERSISTENT" in content[m.start():m.end() + 20].upper():
            cs.entry_points.append(f"PERSISTENT RUN: {target}")
        cs.dependencies.append(target)
    cs.dependencies = list(set(cs.dependencies))

    # ─── AppServer calls ───
    for m in re.finditer(r"RUN\s+[\w/.-]+\s+ON\s+(?:SERVER\s+)?([\w-]+)", content, re.IGNORECASE):
        cs.entry_points.append(f"APPSERVER: {m.group(1)}")

    # ─── DYNAMIC-FUNCTION calls (reflection) ───
    for m in re.finditer(r"DYNAMIC-FUNCTION\s*\(\s*[\"']([\w-]+)[\"']", content, re.IGNORECASE):
        cs.dependencies.append(f"DYNAMIC: {m.group(1)}")

    # ─── DO TRANSACTION blocks ───
    tx_count = len(re.findall(r"DO\s+TRANSACTION", content, re.IGNORECASE))
    if tx_count:
        cs.key_comments.append(f"TRANSACTIONS: {tx_count} explicit transaction blocks")

    # ─── DATASET / DATA-SOURCE (ProDataSet) ───
    for m in re.finditer(r"DEFINE\s+DATASET\s+([\w-]+)", content, re.IGNORECASE):
        cs.key_comments.append(f"DATASET: {m.group(1)}")
    for m in re.finditer(r"DEFINE\s+DATA-SOURCE\s+([\w-]+)", content, re.IGNORECASE):
        cs.key_comments.append(f"DATA-SOURCE: {m.group(1)}")

    # ─── Include files ───
    cs.imports = re.findall(r"\{([\w/.-]+\.i)\}", content)

    # ─── PUBLISH/SUBSCRIBE events ───
    for m in re.finditer(r"(?:PUBLISH|SUBSCRIBE)\s+[\"']([\w-]+)[\"']", content, re.IGNORECASE):
        cs.entry_points.append(f"EVENT: {m.group(1)}")

    # ─── ON triggers ───
    for m in re.finditer(r"ON\s+(\w+)\s+OF\s+([\w-]+)", content, re.IGNORECASE):
        cs.entry_points.append(f"TRIGGER: {m.group(1)} OF {m.group(2)}")

    # ─── ASSIGN blocks (multi-field assignment) ───
    assign_count = len(re.findall(r"^\s*ASSIGN\s", content, re.IGNORECASE | re.MULTILINE))
    if assign_count > 5:
        cs.key_comments.append(f"DATA TRANSFORM: {assign_count} ASSIGN blocks")

    # ─── INDEX definitions in temp-tables ───
    for m in re.finditer(r"INDEX\s+([\w-]+)(?:\s+IS\s+(?:PRIMARY|UNIQUE))?\s+([\w-]+(?:\s+[\w-]+)*)", content, re.IGNORECASE):
        cs.key_comments.append(f"INDEX: {m.group(1)} on {m.group(2).strip()[:80]}")

    # ─── Hardcoded values ───
    for m in re.finditer(r"(?:DEFINE\s+VARIABLE|DEF\s+VAR)\s+([\w-]+)\s+AS\s+\w+.*?INIT(?:IAL)?\s+([\"']?[\w.-]+[\"']?)", content, re.IGNORECASE):
        cs.hardcoded_values.append(HardcodedValue(name=m.group(1), value=m.group(2)))

    # ─── Key comments ───
    for m in re.finditer(r"/\*\s*(TODO|FIXME|HACK|BUSINESS\s*RULE)[:\s]*(.*?)\*/", content, re.IGNORECASE | re.DOTALL):
        cs.key_comments.append(f"{m.group(1)}: {m.group(2).strip()[:200]}")

    return cs
