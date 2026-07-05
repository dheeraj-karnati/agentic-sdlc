"""Unstructured.io integration for D1: Ingest agent.

Provides typed document elements (Title, NarrativeText, Table, ListItem, etc.)
instead of raw text blobs, giving D2: Discover structured input for extraction.
"""

import logging
import tempfile
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# File extensions that should short-circuit (audio, video, image)
_MEDIA_EXTENSIONS: set[str] = {
    ".mp3",
    ".mp4",
    ".wav",
    ".ogg",
    ".flac",
    ".webm",
    ".avi",
    ".mov",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".svg",
}


class ParsedElement(BaseModel):
    """A single typed element extracted from a document."""

    category: str
    text: str
    metadata: dict = Field(default_factory=dict)
    page_number: int | None = None


class ParsedDocument(BaseModel):
    """Result of parsing a file with unstructured."""

    text: str = ""
    elements: list[ParsedElement] = Field(default_factory=list)
    element_summary: dict[str, int] = Field(default_factory=dict)
    parser_used: str = "unstructured"
    parse_errors: list[str] = Field(default_factory=list)


def parse_file(file_path: Path) -> ParsedDocument:
    """Parse a file using unstructured.io partition.

    Short-circuits audio/video/image files. Falls back to plain text reading
    on any exception.
    """
    # Short-circuit media files
    suffix = file_path.suffix.lower()
    if suffix in _MEDIA_EXTENSIONS:
        return ParsedDocument(
            text="",
            elements=[],
            element_summary={},
            parser_used="fallback",
            parse_errors=[f"Media file skipped: {suffix}"],
        )

    try:
        from unstructured.partition.auto import partition

        raw_elements = partition(filename=str(file_path))

        elements: list[ParsedElement] = []
        for el in raw_elements:
            meta = el.metadata.to_dict() if hasattr(el.metadata, "to_dict") else {}
            page_num = meta.get("page_number")
            elements.append(
                ParsedElement(
                    category=el.category,
                    text=el.text,
                    metadata=meta,
                    page_number=page_num,
                )
            )

        text = "\n\n".join(el.text for el in elements if el.text)
        summary = dict(Counter(el.category for el in elements))

        return ParsedDocument(
            text=text,
            elements=elements,
            element_summary=summary,
            parser_used="unstructured",
            parse_errors=[],
        )

    except Exception as exc:
        logger.warning("Unstructured parsing failed for %s: %s", file_path, exc)
        # Fallback: read as plain text
        try:
            fallback_text = file_path.read_text(errors="replace")
        except Exception:
            fallback_text = ""

        return ParsedDocument(
            text=fallback_text,
            elements=[],
            element_summary={},
            parser_used="fallback",
            parse_errors=[str(exc)],
        )


def parse_content(content: str, filename: str) -> ParsedDocument:
    """Parse in-memory content by writing to a temp file.

    This is needed because _run_ingest_agent has file content in memory
    (from Artifact.content), not file paths.
    """
    if not content:
        return ParsedDocument(
            text="",
            elements=[],
            element_summary={},
            parser_used="fallback",
            parse_errors=["Empty content"],
        )

    # Determine extension from filename
    ext = Path(filename).suffix or ".txt"

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        return parse_file(tmp_path)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
