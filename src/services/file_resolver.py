"""FileResolverService: resolves file sources to S3 keys.

Handles three input types:
1. Direct upload (multipart) → upload to S3
2. HTTP/HTTPS URL → download then upload to S3
3. S3 key → verify exists

All files end up in S3 with a canonical key:
  projects/{project_id}/uploads/{filename}
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from src.services.storage import get_storage

logger = logging.getLogger(__name__)

# Max download size for URL-based imports (500MB)
MAX_URL_DOWNLOAD_BYTES = 500 * 1024 * 1024

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".xlsx", ".xls", ".txt", ".md", ".html", ".htm", ".rtf", ".csv",
    # Code
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cs", ".go", ".rs", ".rb",
    ".php", ".c", ".cpp", ".h", ".hpp", ".swift", ".kt", ".scala", ".sh", ".sql",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".env", ".ini", ".cfg",
    # Media
    ".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac",
    ".mp4", ".mov", ".avi", ".webm", ".mkv",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp",
    # Archives
    ".zip", ".tar", ".gz", ".tar.gz", ".tgz",
}


class ResolvedFile(BaseModel):
    """A file that has been resolved to an S3 location."""

    s3_key: str = ""
    original_filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    source_type: str = ""  # upload, url, s3


class FileResolverService:
    """Resolves file inputs from various sources into S3-stored files."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.storage = get_storage()
        self._prefix = f"projects/{project_id}/uploads"

    async def resolve_upload(
        self, filename: str, content: bytes, content_type: str = ""
    ) -> ResolvedFile:
        """Store an uploaded file in S3.

        Args:
            filename: Original filename.
            content: Raw file bytes.
            content_type: MIME type (auto-detected if empty).
        """
        safe_name = self._safe_filename(filename)
        s3_key = f"{self._prefix}/{safe_name}"

        if not content_type:
            content_type = self._guess_content_type(filename)

        self.storage.upload_bytes(content, s3_key, content_type=content_type)

        return ResolvedFile(
            s3_key=s3_key,
            original_filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            source_type="upload",
        )

    async def resolve_url(self, url: str, filename: str = "") -> ResolvedFile:
        """Download a file from a URL and store in S3.

        Supports: HTTP, HTTPS, Google Drive shareable links, Dropbox links.
        """
        # Normalize known cloud storage URLs
        download_url = self._normalize_url(url)

        if not filename:
            filename = self._filename_from_url(url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client:
            # Stream download to temp file to avoid memory issues
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
                total_bytes = 0

                async with client.stream("GET", download_url) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")

                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        total_bytes += len(chunk)
                        if total_bytes > MAX_URL_DOWNLOAD_BYTES:
                            Path(tmp_path).unlink(missing_ok=True)
                            raise ValueError(
                                f"File exceeds maximum download size "
                                f"({MAX_URL_DOWNLOAD_BYTES // 1024 // 1024}MB)"
                            )
                        tmp.write(chunk)

        try:
            safe_name = self._safe_filename(filename)
            s3_key = f"{self._prefix}/{safe_name}"
            self.storage.upload_file(tmp_path, s3_key, content_type=content_type)

            return ResolvedFile(
                s3_key=s3_key,
                original_filename=filename,
                content_type=content_type or self._guess_content_type(filename),
                size_bytes=total_bytes,
                source_type="url",
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def resolve_s3(self, s3_key: str) -> ResolvedFile:
        """Verify an existing S3 object and return its metadata."""
        if not self.storage.exists(s3_key):
            raise FileNotFoundError(f"S3 object not found: {s3_key}")

        meta = self.storage.get_metadata(s3_key)
        filename = s3_key.rsplit("/", 1)[-1] if "/" in s3_key else s3_key

        return ResolvedFile(
            s3_key=s3_key,
            original_filename=filename,
            content_type=meta.get("content_type", ""),
            size_bytes=meta.get("size_bytes", 0),
            source_type="s3",
        )

    def get_download_path(self, s3_key: str) -> str:
        """Download an S3 file to a temp path for processing.

        Caller must clean up the temp file.
        """
        suffix = "." + s3_key.rsplit(".", 1)[-1] if "." in s3_key else ""
        return self.storage.download_to_tempfile(s3_key, suffix=suffix)

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Get a presigned URL for secure, temporary access."""
        return self.storage.generate_presigned_url(s3_key, expires_in)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Sanitize filename and add UUID prefix for uniqueness."""
        name = Path(filename).name
        # Remove problematic characters
        safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name)
        uid = uuid.uuid4().hex[:8]
        return f"{uid}_{safe}"

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".html": "text/html",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".json": "application/json",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".zip": "application/zip",
        }.get(ext, "application/octet-stream")

    @staticmethod
    def _filename_from_url(url: str) -> str:
        """Extract a filename from a URL."""
        path = url.split("?")[0].split("#")[0]
        name = path.rsplit("/", 1)[-1] if "/" in path else "download"
        if "." not in name:
            name = f"{name}.bin"
        return name

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Convert cloud storage sharing URLs to direct download URLs."""
        # Google Drive: convert /file/d/{id}/view to direct download
        if "drive.google.com/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        # Dropbox: replace dl=0 with dl=1
        if "dropbox.com" in url and "dl=0" in url:
            return url.replace("dl=0", "dl=1")

        return url
