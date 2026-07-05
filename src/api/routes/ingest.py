"""File ingestion routes — upload files, import from URLs, or reference S3 objects.

All files are resolved to S3 storage, then the Digitize Agent processes them.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.context_store.database import get_db
from src.context_store.models import Artifact, ArtifactType
from src.services.file_resolver import FileResolverService, ResolvedFile

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/ingest",
    tags=["ingest"],
)


# ─── Request/Response Schemas ───


class URLSource(BaseModel):
    url: str
    filename: str = ""  # optional override


class S3Source(BaseModel):
    s3_key: str


class IngestRequest(BaseModel):
    """Import files from URLs or existing S3 keys."""

    urls: list[URLSource] = Field(default_factory=list)
    s3_keys: list[S3Source] = Field(default_factory=list)


class ResolvedFileResponse(BaseModel):
    s3_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    source_type: str


class IngestResponse(BaseModel):
    resolved_files: list[ResolvedFileResponse]
    total_files: int
    total_bytes: int
    errors: list[str]


# ─── Endpoints ───


@router.post("/upload", response_model=IngestResponse, status_code=201)
async def upload_files(
    project_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload one or more files directly. Files are stored in S3 and queued for processing.

    Supports: PDF, DOCX, XLSX, TXT, MD, HTML, Python, JS, TS, Java,
    MP3, WAV, MP4, MOV, PNG, JPG, SVG, ZIP, and more.

    Max file size: governed by the reverse proxy (recommend 500MB).
    """
    resolver = FileResolverService(str(project_id))
    resolved: list[ResolvedFile] = []
    errors: list[str] = []

    for upload in files:
        try:
            content = await upload.read()
            filename = upload.filename or "unnamed"

            # ─── ZIP extraction: expand archive into individual files ───
            if filename.lower().endswith((".zip",)):
                from src.services.archive_extractor import extract_zip

                extraction = extract_zip(content, filename)
                errors.extend(extraction.errors)

                if not extraction.files:
                    errors.append(f"No extractable files found in {filename}")
                    continue

                logger.info("Extracted %d files from %s", len(extraction.files), filename)

                for ef in extraction.files:
                    # Store each extracted file in S3
                    s3_key = f"projects/{project_id}/uploads/extracted/{ef.relative_path}"
                    try:
                        from src.services.storage import get_storage
                        storage = get_storage()
                        storage.upload_bytes(ef.content, s3_key, _guess_content_type(ef.relative_path))
                    except Exception as s3_err:
                        errors.append(f"Failed to store extracted file {ef.relative_path}: {s3_err}")
                        continue

                    art_type = _classify_artifact_type(ef.relative_path)
                    inline = _try_inline_content(ef.content, ef.relative_path, ef.size_bytes)

                    artifact = Artifact(
                        project_id=project_id,
                        type=art_type,
                        name=ef.relative_path,
                        s3_key=s3_key,
                        content=inline,
                        metadata_={
                            "original_filename": ef.relative_path,
                            "content_type": _guess_content_type(ef.relative_path),
                            "size_bytes": ef.size_bytes,
                            "source_type": "extracted",
                            "archive_source": ef.archive_source,
                        },
                    )
                    db.add(artifact)

                # Create a summary ResolvedFile for the ZIP itself
                zip_result = await resolver.resolve_upload(
                    filename=filename, content=content,
                    content_type=upload.content_type or "application/zip",
                )
                resolved.append(zip_result)
                continue

            # ─── Regular file upload ───
            result = await resolver.resolve_upload(
                filename=filename,
                content=content,
                content_type=upload.content_type or "",
            )
            resolved.append(result)

            art_type = _classify_artifact_type(filename)
            inline_content = _try_inline_content(content, filename, result.size_bytes)

            artifact = Artifact(
                project_id=project_id,
                type=art_type,
                name=filename,
                s3_key=result.s3_key,
                content=inline_content,
                metadata_={
                    "original_filename": upload.filename,
                    "content_type": result.content_type,
                    "size_bytes": result.size_bytes,
                    "source_type": result.source_type,
                },
            )
            db.add(artifact)

        except Exception as e:
            errors.append(f"Failed to upload {upload.filename}: {e}")
            logger.error("Upload failed for %s: %s", upload.filename, e)

    await db.flush()

    total_bytes = sum(r.size_bytes for r in resolved)

    return {
        "resolved_files": [r.model_dump() for r in resolved],
        "total_files": len(resolved),
        "total_bytes": total_bytes,
        "errors": errors,
    }


# ─── Helpers ───

# Extended text extensions including enterprise languages
_TEXT_EXTENSIONS: tuple[str, ...] = (
    ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".sql", ".json", ".yaml", ".yml",
    ".html", ".htm", ".css", ".xml", ".csv", ".toml", ".ini", ".sh", ".java", ".go",
    ".rb", ".cs", ".rs", ".kt", ".swift", ".scala", ".groovy", ".php", ".c", ".cpp", ".h", ".hpp",
    # Enterprise languages
    ".cbl", ".cob", ".cpy", ".jcl", ".proc",  # COBOL / Mainframe
    ".rpg", ".rpgle", ".clp",  # RPG (AS/400)
    ".p", ".w", ".i", ".cls",  # Progress 4GL
    ".pls", ".pks", ".pkb", ".trg", ".fnc", ".prc", ".vw",  # PL/SQL
    ".bas", ".frm", ".vbs", ".asp", ".asa",  # VB6 / Classic ASP
    ".pbl", ".srf", ".srd", ".psr",  # PowerBuilder
    ".jsp", ".jspx", ".xhtml", ".ftl", ".vm",  # Java views
    ".bat", ".cmd", ".ps1",  # Scripts
    ".properties", ".cfg", ".conf",  # Config
    ".rst", ".adoc",  # Docs
)

_CODE_EXTENSIONS: set[str] = {
    "py", "js", "ts", "tsx", "jsx", "java", "cs", "go", "rs", "rb", "sql", "php",
    "c", "cpp", "h", "hpp", "swift", "kt", "scala", "groovy",
    "cbl", "cob", "cpy", "jcl", "proc", "rpg", "rpgle",
    "p", "w", "i", "cls", "pls", "pks", "pkb", "trg", "fnc", "prc", "vw",
    "bas", "frm", "vbs", "asp", "asa", "pbl", "srf",
    "bat", "cmd", "ps1", "sh",
}

_IMAGE_EXTENSIONS: set[str] = {"png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "tiff", "ico"}


def _classify_artifact_type(filename: str) -> ArtifactType:
    """Determine ArtifactType from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in _CODE_EXTENSIONS:
        return ArtifactType.CODE
    if ext in _IMAGE_EXTENSIONS:
        return ArtifactType.DIAGRAM
    if ext in ("sql",):
        return ArtifactType.SCHEMA
    return ArtifactType.DOCUMENT


def _try_inline_content(content: bytes, filename: str, size_bytes: int) -> str | None:
    """Try to store file content inline if it's text and under 500KB."""
    fname_lower = filename.lower()
    is_text = fname_lower.endswith(_TEXT_EXTENSIONS)
    if size_bytes < 500_000 and is_text:
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            pass
    return None


def _guess_content_type(filename: str) -> str:
    """Guess MIME content type from filename."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mapping = {
        "java": "text/x-java-source", "py": "text/x-python", "js": "text/javascript",
        "ts": "text/typescript", "sql": "text/x-sql", "xml": "application/xml",
        "json": "application/json", "yaml": "text/yaml", "yml": "text/yaml",
        "html": "text/html", "css": "text/css", "md": "text/markdown",
        "txt": "text/plain", "properties": "text/plain", "cfg": "text/plain",
        "cbl": "text/x-cobol", "cob": "text/x-cobol", "cpy": "text/x-cobol",
        "jcl": "text/plain", "rpg": "text/plain",
        "p": "text/plain", "w": "text/plain", "i": "text/plain",
        "pls": "text/x-plsql", "pks": "text/x-plsql", "pkb": "text/x-plsql",
        "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "zip": "application/zip",
    }
    return mapping.get(ext, "application/octet-stream")


@router.post("/import", response_model=IngestResponse, status_code=201)
async def import_from_sources(
    project_id: uuid.UUID,
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Import files from URLs or existing S3 keys.

    URL sources: supports HTTP/HTTPS, Google Drive sharing links,
    Dropbox links. Files are downloaded and stored in S3.

    S3 sources: references existing objects in the project's S3 bucket.
    Objects are verified but not re-uploaded.
    """
    resolver = FileResolverService(str(project_id))
    resolved: list[ResolvedFile] = []
    errors: list[str] = []

    # Resolve URL sources
    for url_src in request.urls:
        try:
            result = await resolver.resolve_url(
                url=url_src.url,
                filename=url_src.filename,
            )
            resolved.append(result)
        except Exception as e:
            errors.append(f"Failed to import {url_src.url}: {e}")
            logger.error("URL import failed for %s: %s", url_src.url, e)

    # Resolve S3 sources
    for s3_src in request.s3_keys:
        try:
            result = await resolver.resolve_s3(s3_key=s3_src.s3_key)
            resolved.append(result)
        except Exception as e:
            errors.append(f"Failed to resolve {s3_src.s3_key}: {e}")
            logger.error("S3 resolve failed for %s: %s", s3_src.s3_key, e)

    total_bytes = sum(r.size_bytes for r in resolved)

    return {
        "resolved_files": [r.model_dump() for r in resolved],
        "total_files": len(resolved),
        "total_bytes": total_bytes,
        "errors": errors,
    }


@router.get("/files", response_model=list[ResolvedFileResponse])
async def list_uploaded_files(
    project_id: uuid.UUID,
) -> list[dict]:
    """List all files uploaded/imported for this project."""
    from src.services.storage import get_storage

    storage = get_storage()
    prefix = f"projects/{project_id}/uploads"
    objects = storage.list_objects(prefix=prefix, max_keys=500)

    return [
        {
            "s3_key": obj["key"],
            "original_filename": obj["key"].rsplit("/", 1)[-1].split("_", 1)[-1] if "_" in obj["key"].rsplit("/", 1)[-1] else obj["key"].rsplit("/", 1)[-1],
            "content_type": "",
            "size_bytes": obj["size"],
            "source_type": "s3",
        }
        for obj in objects
    ]


@router.get("/files/{s3_key:path}/download-url")
async def get_download_url(
    project_id: uuid.UUID,
    s3_key: str,
) -> dict:
    """Get a presigned URL to download a file. Valid for 1 hour."""
    from src.services.storage import get_storage

    storage = get_storage()
    if not storage.exists(s3_key):
        raise HTTPException(status_code=404, detail="File not found")

    url = storage.generate_presigned_url(s3_key, expires_in=3600)
    return {"download_url": url, "expires_in": 3600}
