"""Deep RPG / AS400 code structure extractor.

Handles both fixed-format RPG (RPG III/IV) and free-format RPG (RPG Free).
Extracts file declarations, data structures, calculations, SQL, indicators.
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
    """Extract structure from RPG source (fixed and free format)."""
    cs = CodeStructure(language="rpg", file_path=file_path)

    # Detect format
    is_free = bool(re.search(r"(?:DCL-PROC|DCL-S|DCL-DS|DCL-F)", content, re.IGNORECASE))
    cs.key_comments.append(f"FORMAT: {'free' if is_free else 'fixed'}")

    if is_free:
        _extract_free_format(content, cs)
    else:
        _extract_fixed_format(content, cs)

    # ─── Common patterns (both formats) ───

    # Embedded SQL
    for m in re.finditer(r"EXEC\s+SQL(.*?)END-EXEC", content, re.IGNORECASE | re.DOTALL):
        sql = m.group(1).strip()[:300]
        cs.sql_queries.append(sql)

    # Program calls
    for m in re.finditer(r"CALL(?:P)?\s*\(?['\"]?(\w+)['\"]?", content, re.IGNORECASE):
        cs.dependencies.append(m.group(1))
    cs.dependencies = list(set(cs.dependencies))

    # Indicator usage (*INxx)
    indicators = set(re.findall(r"\*IN(\d{2})", content))
    if indicators:
        cs.key_comments.append(f"INDICATORS: *IN{', *IN'.join(sorted(indicators))}")

    # Key comments
    for m in re.finditer(r"//\s*(TODO|FIXME|HACK|BUSINESS\s*RULE)[:\s]*(.*)", content, re.IGNORECASE):
        cs.key_comments.append(f"{m.group(1)}: {m.group(2).strip()[:200]}")

    # Activation group
    for m in re.finditer(r"ACTGRP\s*\(\s*['\"]?(\w+)['\"]?\s*\)", content, re.IGNORECASE):
        cs.key_comments.append(f"ACTGRP: {m.group(1)}")

    return cs


def _extract_free_format(content: str, cs: CodeStructure) -> None:
    """Extract from free-format RPG (DCL-xxx style)."""
    # Program name from control spec
    m = re.search(r"CTL-OPT.*?MAIN\s*\(\s*(\w+)\s*\)", content, re.IGNORECASE | re.DOTALL)
    if m:
        cs.class_name = m.group(1)
        cs.entry_points.append(f"MAIN: {m.group(1)}")

    # File declarations
    for m in re.finditer(
        r"DCL-F\s+(\w+)\s+(?:(\w+)\s+)?(?:USAGE\s*\(\s*(\*\w+)\s*\))?",
        content, re.IGNORECASE,
    ):
        fname = m.group(1)
        ftype = m.group(2) or ""
        usage = m.group(3) or ""
        cs.dependencies.append(f"FILE: {fname} ({ftype} {usage})".strip())

    # Data structures
    for m in re.finditer(r"DCL-DS\s+(\w+)(?:\s+(?:LIKEDS|LIKEREC)\s*\(\s*(\w+)\s*\))?", content, re.IGNORECASE):
        ds_name = m.group(1)
        like = m.group(2) or ""
        cs.key_comments.append(f"DATA-STRUCT: {ds_name}" + (f" LIKE {like}" if like else ""))

    # Standalone variables
    for m in re.finditer(r"DCL-S\s+(\w+)\s+(\w+)(?:\s*\(\s*(\d+)\s*\))?\s*(?:INZ\s*\(\s*([^)]+)\s*\))?", content, re.IGNORECASE):
        name = m.group(1)
        vtype = m.group(2)
        init = m.group(4)
        if init:
            cs.hardcoded_values.append(HardcodedValue(name=name, value=f"{vtype}={init}"))

    # Procedures (subprocedures)
    for m in re.finditer(r"DCL-PROC\s+(\w+)(?:\s+EXPORT)?", content, re.IGNORECASE):
        cs.methods.append(MethodSignature(name=m.group(1)))

    # Procedure interfaces (params)
    for m in re.finditer(r"DCL-PI\s+(\w+)(.*?)END-PI", content, re.IGNORECASE | re.DOTALL):
        proc_name = m.group(1)
        params_block = m.group(2)
        params = re.findall(r"(\w+)\s+(\w+)", params_block)
        param_str = ", ".join(f"{n} {t}" for n, t in params[:10])
        # Update the method with params
        for method in cs.methods:
            if method.name == proc_name:
                method.params = param_str
                break

    # SELECT/WHEN (business rules)
    for m in re.finditer(r"SELECT\s*;(.*?)ENDSL\s*;", content, re.IGNORECASE | re.DOTALL):
        whens = re.findall(r"WHEN\s+(.+?)\s*;", m.group(1), re.IGNORECASE)
        if whens:
            cs.key_comments.append(f"BUSINESS RULE: SELECT/WHEN with {len(whens)} conditions")

    # Service program exports
    for m in re.finditer(r"DCL-PROC\s+(\w+)\s+EXPORT", content, re.IGNORECASE):
        cs.entry_points.append(f"EXPORT: {m.group(1)}")


def _extract_fixed_format(content: str, cs: CodeStructure) -> None:
    """Extract from fixed-format RPG (column-based)."""
    # H-spec (control)
    for m in re.finditer(r"^H\s+(.+)", content, re.MULTILINE):
        if "ACTGRP" in m.group(1).upper():
            cs.key_comments.append(f"H-SPEC: {m.group(1).strip()[:100]}")

    # F-spec (file declarations)
    # Columns: 6=name, 16=type(I/O/U/C), 17=designation, 18=EOF, 19-20=addition
    for m in re.finditer(r"^F(\w+)\s+(\w+)", content, re.MULTILINE):
        fname = m.group(1).strip()
        ftype = m.group(2).strip()
        if fname and len(fname) > 1:
            cs.dependencies.append(f"FILE: {fname} ({ftype})")

    # D-spec (data definitions)
    for m in re.finditer(r"^D\s*(\w+)\s+(?:S|DS)\s+", content, re.MULTILINE):
        cs.key_comments.append(f"DATA: {m.group(1).strip()}")

    # C-spec subroutines (BEGSR/ENDSR)
    for m in re.finditer(r"^\s*C\s+(\w+)\s+BEGSR", content, re.MULTILINE | re.IGNORECASE):
        cs.methods.append(MethodSignature(name=m.group(1).strip()))

    # C-spec operations: CHAIN, READ, WRITE, UPDATE, DELETE
    for m in re.finditer(r"^\s*C\s+.*?(CHAIN|READE?|WRITE|UPDATE|DELETE)\s+(\w+)", content, re.MULTILINE | re.IGNORECASE):
        op = m.group(1).upper()
        target = m.group(2)
        cs.sql_queries.append(f"{op} {target}")

    # C-spec EVAL with hardcoded values
    for m in re.finditer(r"^\s*C\s+.*?EVAL\s+(\w+)\s*=\s*(\d{3,})", content, re.MULTILINE | re.IGNORECASE):
        cs.hardcoded_values.append(HardcodedValue(name=m.group(1), value=m.group(2)))

    # C-spec SELECT/WHEN
    select_blocks = re.findall(r"SELECT.*?ENDSL", content, re.IGNORECASE | re.DOTALL)
    if select_blocks:
        cs.key_comments.append(f"BUSINESS LOGIC: {len(select_blocks)} SELECT/WHEN blocks")
