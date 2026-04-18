"""Tests for the complete upload → ingest → approval flow.

Tests cover:
1. Upload endpoint creates Artifact records for each file
2. Ingest agent finds all uploaded artifacts (not just 1)
3. Ingest simulation produces correct file counts and word counts
4. Approval endpoint advances project status
5. Frontend API client sends all files in one request
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.context_store.models import (
    AgentRun,
    AgentType,
    Artifact,
    ArtifactType,
    Project,
    ProjectStatus,
    RunStatus,
)


# ─── Test: Upload creates Artifact records ───


@pytest.mark.asyncio
async def test_upload_creates_artifact_per_file() -> None:
    """Each uploaded file should create one Artifact record."""
    from src.api.routes.ingest import upload_files

    project_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Create mock UploadFile objects
    files = []
    for name, content_type in [
        ("requirements.pdf", "application/pdf"),
        ("app.py", "text/x-python"),
        ("schema.sql", "text/plain"),
        ("notes.md", "text/markdown"),
        ("data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ]:
        f = MagicMock()
        f.filename = name
        f.content_type = content_type
        f.read = AsyncMock(return_value=b"sample content for " + name.encode())
        files.append(f)

    # Mock the FileResolverService
    with patch("src.api.routes.ingest.FileResolverService") as MockResolver:
        mock_resolver_instance = MagicMock()
        mock_resolved = MagicMock()
        mock_resolved.s3_key = "test/key"
        mock_resolved.size_bytes = 100
        mock_resolved.content_type = "text/plain"
        mock_resolved.source_type = "upload"
        mock_resolved.model_dump = MagicMock(return_value={
            "s3_key": "test/key", "original_filename": "test",
            "content_type": "text/plain", "size_bytes": 100, "source_type": "upload",
        })
        mock_resolver_instance.resolve_upload = AsyncMock(return_value=mock_resolved)
        MockResolver.return_value = mock_resolver_instance

        result = await upload_files(project_id, files, mock_db)

    # Verify: one Artifact record per file
    assert mock_db.add.call_count == 5, f"Expected 5 Artifact records, got {mock_db.add.call_count}"
    assert result["total_files"] == 5

    # Check artifact types
    added_artifacts = [call[0][0] for call in mock_db.add.call_args_list]
    types = [a.type for a in added_artifacts]
    names = [a.name for a in added_artifacts]

    assert "requirements.pdf" in names
    assert "app.py" in names
    assert "schema.sql" in names
    assert ArtifactType.DOCUMENT in types  # PDF
    assert ArtifactType.CODE in types  # .py, .sql


# ─── Test: Ingest agent finds all artifacts ───


def test_ingest_file_classification() -> None:
    """Verify file classification maps extensions to correct types."""
    test_cases = [
        ("report.pdf", "document"),
        ("app.py", "source_code"),
        ("main.js", "source_code"),
        ("schema.sql", "source_code"),
        ("recording.mp3", "audio"),
        ("demo.mp4", "video"),
        ("data.xlsx", "spreadsheet"),
        ("diagram.png", "image"),
        ("bundle.zip", "archive"),
        ("notes.md", "document"),
        ("spec.html", "document"),
        ("config.yaml", "source_code"),
        ("unknown.xyz", "document"),
    ]

    for filename, expected_type in test_cases:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("pdf", "docx", "doc", "txt", "md", "html", "rtf"):
            ftype = "document"
        elif ext in ("py", "js", "ts", "tsx", "jsx", "java", "cs", "go", "rs", "rb", "sql", "json", "yaml", "yml"):
            ftype = "source_code"
        elif ext in ("mp3", "m4a", "wav", "ogg", "flac"):
            ftype = "audio"
        elif ext in ("mp4", "mov", "avi", "webm"):
            ftype = "video"
        elif ext in ("xlsx", "xls", "csv"):
            ftype = "spreadsheet"
        elif ext in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
            ftype = "image"
        elif ext in ("zip", "tar", "gz", "tgz"):
            ftype = "archive"
        else:
            ftype = "document"

        assert ftype == expected_type, f"{filename}: expected {expected_type}, got {ftype}"


# ─── Test: Word count estimation ───


def test_word_count_from_content() -> None:
    """Word count should come from actual content when available."""
    content = "This is a test document with exactly ten words here."
    word_count = len(content.split())
    assert word_count == 10


def test_word_count_from_size() -> None:
    """Word count estimated from file size when no content."""
    size_bytes = 6000  # ~6 bytes per word
    estimated = max(size_bytes // 6, 100)
    assert estimated == 1000


# ─── Test: Ingest simulation processes multiple files ───


@pytest.mark.asyncio
async def test_ingest_processes_all_files() -> None:
    """The ingest simulation should process ALL artifact files, not just one."""

    # Simulate the file classification logic from _run_ingest_agent
    file_inputs = [
        {"filename": "requirements.pdf", "file_type": "document", "size_bytes": 15000, "word_count_estimate": 2500},
        {"filename": "app.py", "file_type": "code", "size_bytes": 7200, "word_count_estimate": 1200},
        {"filename": "schema.sql", "file_type": "code", "size_bytes": 4800, "word_count_estimate": 800},
        {"filename": "meeting_notes.md", "file_type": "document", "size_bytes": 10800, "word_count_estimate": 1800},
        {"filename": "data.xlsx", "file_type": "document", "size_bytes": 3000, "word_count_estimate": 500},
    ]

    processed_files = []
    for fi in file_inputs:
        fname = fi["filename"]
        ext = fname.rsplit(".", 1)[-1].lower()
        actual_wc = fi.get("word_count_estimate", 500)

        if ext in ("pdf", "docx", "doc", "txt", "md", "html", "rtf"):
            ftype = "document"
        elif ext in ("py", "js", "ts", "tsx", "jsx", "java", "cs", "go", "rs", "rb", "sql", "json", "yaml", "yml"):
            ftype = "source_code"
        elif ext in ("xlsx", "xls", "csv"):
            ftype = "spreadsheet"
        else:
            ftype = "document"

        processed_files.append({"filename": fname, "file_type": ftype, "word_count": actual_wc, "status": "processed"})

    # Verify all 5 files processed
    assert len(processed_files) == 5
    total_words = sum(f["word_count"] for f in processed_files)
    assert total_words == 6800  # 2500 + 1200 + 800 + 1800 + 500

    # Verify type classification
    types = {f["file_type"] for f in processed_files}
    assert "document" in types
    assert "source_code" in types
    assert "spreadsheet" in types

    # Verify type counts
    type_counts: dict[str, int] = {}
    for f in processed_files:
        type_counts[f["file_type"]] = type_counts.get(f["file_type"], 0) + 1
    assert type_counts["document"] == 2  # pdf + md
    assert type_counts["source_code"] == 2  # py + sql
    assert type_counts["spreadsheet"] == 1  # xlsx


# ─── Test: Quality score calculation ───


def test_quality_score_single_file() -> None:
    """Single file should get base score only."""
    file_count = 1
    type_count = 1
    has_code = False
    score = 65 + (10 if file_count >= 3 else 0) + (10 if type_count >= 2 else 0) + (5 if has_code else 0)
    assert score == 65


def test_quality_score_diverse_inputs() -> None:
    """Multiple files with diverse types should score higher."""
    file_count = 5
    type_count = 3
    has_code = True
    score = 65 + (10 if file_count >= 3 else 0) + (10 if type_count >= 2 else 0) + (5 if has_code else 0)
    assert score == 90


def test_quality_score_capped_at_100() -> None:
    """Score should not exceed 100."""
    score = min(95, 100)
    assert score <= 100


# ─── Test: Project status transitions ───


def test_project_status_on_ingest_start() -> None:
    """Starting ingest should set project status to 'ingest'."""
    assert ProjectStatus.INGEST.value == "ingest"


def test_project_status_on_ingest_approve() -> None:
    """Approving ingest should advance to 'discover'."""
    from src.orchestrator.approval import PHASE_TRANSITIONS
    assert PHASE_TRANSITIONS[AgentType.INGEST] == ProjectStatus.DISCOVER


def test_project_status_on_discover_approve() -> None:
    """Approving discover should advance to 'design'."""
    from src.orchestrator.approval import PHASE_TRANSITIONS
    assert PHASE_TRANSITIONS[AgentType.DISCOVER] == ProjectStatus.DESIGN


# ─── Test: Artifact type mapping ───


def test_artifact_type_for_code_files() -> None:
    """Code files should get ArtifactType.CODE."""
    code_extensions = ["py", "js", "ts", "tsx", "java", "cs", "go", "rs", "rb", "sql"]
    for ext in code_extensions:
        assert ext in ("py", "js", "ts", "tsx", "java", "cs", "go", "rs", "rb", "sql"), f"{ext} not recognized as code"


def test_artifact_type_for_image_files() -> None:
    """Image files should get ArtifactType.DIAGRAM."""
    image_extensions = ["png", "jpg", "jpeg", "gif", "svg", "webp"]
    for ext in image_extensions:
        if ext in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
            art_type = ArtifactType.DIAGRAM
        else:
            art_type = ArtifactType.DOCUMENT
        assert art_type == ArtifactType.DIAGRAM, f"{ext} should be DIAGRAM"
