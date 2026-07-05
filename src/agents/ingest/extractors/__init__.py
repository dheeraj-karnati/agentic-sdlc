"""Extractor registry for enterprise language code structure extraction.

Each extractor is a function: extract(content: str, file_path: str) -> CodeStructure
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.ingest.skills.code_structure_skill import CodeStructure

logger = logging.getLogger(__name__)

# Type alias for extractor functions
ExtractorFn = Callable[[str, str], "CodeStructure"]

# Lazy registry — imports happen on first use to avoid circular imports
_registry: dict[str, ExtractorFn] | None = None


def _build_registry() -> dict[str, ExtractorFn]:
    from src.agents.ingest.extractors.cobol_extractor import extract as cobol_extract
    from src.agents.ingest.extractors.dotnet_extractor import extract as dotnet_extract
    from src.agents.ingest.extractors.java_extractor import extract as java_extract
    from src.agents.ingest.extractors.plsql_extractor import extract as plsql_extract
    from src.agents.ingest.extractors.progress_extractor import extract as progress_extract
    from src.agents.ingest.extractors.rpg_extractor import extract as rpg_extract
    from src.agents.ingest.skills.code_structure_skill import (
        _extract_python,
        _extract_sql,
        _extract_vb6,
    )

    return {
        # Java ecosystem
        "java": java_extract,
        "kotlin": java_extract,
        "scala": java_extract,
        "groovy": java_extract,
        # Mainframe
        "cobol": cobol_extract,
        "cobol_copybook": cobol_extract,
        "jcl": cobol_extract,
        # Oracle
        "plsql": plsql_extract,
        # Progress
        "progress_4gl": progress_extract,
        "progress_class": progress_extract,
        "progress_include": progress_extract,
        # .NET
        "csharp": dotnet_extract,
        "aspnet": dotnet_extract,
        # AS/400
        "rpg": rpg_extract,
        # VB6 / Classic ASP
        "vb6": _extract_vb6,
        "vbscript": _extract_vb6,
        "asp_classic": _extract_vb6,
        # Python
        "python": _extract_python,
        # SQL
        "sql": _extract_sql,
        "sql_view": _extract_sql,
    }


def get_extractor(language: str) -> ExtractorFn:
    """Get the extractor function for a language. Falls back to generic."""
    global _registry
    if _registry is None:
        _registry = _build_registry()

    extractor = _registry.get(language)
    if extractor:
        return extractor

    # Fallback to generic
    from src.agents.ingest.skills.code_structure_skill import _extract_generic
    return lambda content, path: _extract_generic(content, path, language)
