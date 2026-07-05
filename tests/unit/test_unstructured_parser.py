"""Tests for the unstructured.io parser integration."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.agents.ingest.unstructured_parser import (
    ParsedDocument,
    ParsedElement,
    parse_content,
    parse_file,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "d1"


class TestParseFile:
    """Tests for parse_file function."""

    def test_md_file_parsing(self) -> None:
        """MD file should produce Title, NarrativeText, and Table elements."""
        result = parse_file(FIXTURES_DIR / "sample.md")

        assert isinstance(result, ParsedDocument)
        assert result.parser_used == "unstructured"
        assert len(result.elements) > 0
        assert result.text  # non-empty text

        categories = {el.category for el in result.elements}
        # Markdown should produce at least Title and NarrativeText
        assert "Title" in categories or "NarrativeText" in categories

        # element_summary should have counts
        assert len(result.element_summary) > 0
        total_count = sum(result.element_summary.values())
        assert total_count == len(result.elements)

    def test_sql_file_parsing(self) -> None:
        """SQL file should parse without error (may fallback for unknown types)."""
        result = parse_file(FIXTURES_DIR / "sample.sql")

        assert isinstance(result, ParsedDocument)
        assert result.text  # non-empty — either parsed or fallback reads it
        # SQL is not a well-known type for unstructured, so it may fallback
        assert result.parser_used in ("unstructured", "fallback")

    def test_audio_file_shortcircuit(self) -> None:
        """Audio/video/image files should short-circuit to fallback."""
        for ext in [".mp3", ".mp4", ".png", ".jpg", ".wav", ".svg"]:
            fake_path = Path(f"/tmp/test_file{ext}")
            result = parse_file(fake_path)

            assert result.parser_used == "fallback"
            assert result.text == ""
            assert len(result.elements) == 0
            assert len(result.parse_errors) > 0

    def test_fallback_on_parse_error(self) -> None:
        """If unstructured raises, should fall back to text reading."""
        with patch(
            "unstructured.partition.auto.partition",
            side_effect=RuntimeError("Simulated failure"),
        ):
            # Use the sample.md file so fallback text reading works
            result = parse_file(FIXTURES_DIR / "sample.md")

            assert result.parser_used == "fallback"
            assert "Simulated failure" in result.parse_errors[0]
            assert result.text  # fallback read should have content


class TestParseContent:
    """Tests for parse_content function."""

    def test_parse_content_basic(self) -> None:
        """parse_content should handle in-memory content."""
        content = "# Hello World\n\nThis is a test document.\n"
        result = parse_content(content, "test.md")

        assert isinstance(result, ParsedDocument)
        assert result.text  # non-empty
        assert result.parser_used == "unstructured"

    def test_parse_content_empty(self) -> None:
        """Empty content should return fallback."""
        result = parse_content("", "empty.txt")

        assert result.parser_used == "fallback"
        assert "Empty content" in result.parse_errors

    def test_parse_content_media_extension(self) -> None:
        """Media file extensions should short-circuit."""
        result = parse_content("some bytes", "audio.mp3")

        assert result.parser_used == "fallback"


class TestParsedElementModel:
    """Tests for Pydantic models."""

    def test_parsed_element_creation(self) -> None:
        el = ParsedElement(
            category="Title",
            text="Hello",
            metadata={"page_number": 1},
            page_number=1,
        )
        assert el.category == "Title"
        assert el.text == "Hello"

    def test_parsed_document_defaults(self) -> None:
        doc = ParsedDocument()
        assert doc.text == ""
        assert doc.elements == []
        assert doc.element_summary == {}
        assert doc.parser_used == "unstructured"
        assert doc.parse_errors == []
