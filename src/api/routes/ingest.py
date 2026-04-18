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
            result = await resolver.resolve_upload(
                filename=upload.filename or "unnamed",
                content=content,
                content_type=upload.content_type or "",
            )
            resolved.append(result)

            # Create an Artifact record so the Ingest agent can find this file
            ext = (upload.filename or "").rsplit(".", 1)[-1].lower() if "." in (upload.filename or "") else ""
            if ext in ("py", "js", "ts", "tsx", "java", "cs", "go", "rs", "rb", "sql"):
                art_type = ArtifactType.CODE
            elif ext in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
                art_type = ArtifactType.DIAGRAM
            else:
                art_type = ArtifactType.DOCUMENT

            # Store small text files inline, large/binary files by S3 key
            inline_content = None
            text_extensions = (".md", ".txt", ".py", ".js", ".ts", ".sql", ".json", ".yaml", ".yml",
                               ".html", ".css", ".xml", ".csv", ".toml", ".ini", ".sh", ".java", ".go",
                               ".rb", ".cs", ".rs", ".kt", ".swift")
            fname = (upload.filename or "").lower()
            is_text = (
                result.content_type.startswith(("text/", "application/json", "application/xml"))
                or fname.endswith(text_extensions)
            )
            if result.size_bytes < 500_000 and is_text:
                try:
                    inline_content = content.decode("utf-8", errors="replace")
                except Exception:
                    pass

            artifact = Artifact(
                project_id=project_id,
                type=art_type,
                name=upload.filename or "unnamed",
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
