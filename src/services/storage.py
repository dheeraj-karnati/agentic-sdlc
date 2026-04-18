"""S3-compatible object storage service.

Works with both MinIO (local/iMac) and AWS S3 (cloud) — same API.
All raw uploads and generated artifacts are stored here.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """S3-compatible storage client for MinIO and AWS S3."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )
        self._bucket = settings.s3_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self._bucket)
                logger.info("Created S3 bucket: %s", self._bucket)
            except ClientError as e:
                logger.warning("Could not create bucket: %s", e)

    def upload_file(self, local_path: str | Path, s3_key: str, content_type: str = "") -> str:
        """Upload a local file to S3.

        Returns:
            The s3_key of the uploaded object.
        """
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self._client.upload_file(
            str(local_path), self._bucket, s3_key, ExtraArgs=extra_args or None
        )
        logger.info("Uploaded %s → s3://%s/%s", local_path, self._bucket, s3_key)
        return s3_key

    def upload_bytes(self, data: bytes | BinaryIO, s3_key: str, content_type: str = "") -> str:
        """Upload bytes or a file-like object to S3."""
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        if isinstance(data, bytes):
            from io import BytesIO
            data = BytesIO(data)

        self._client.upload_fileobj(data, self._bucket, s3_key, ExtraArgs=extra_args or None)
        logger.info("Uploaded bytes → s3://%s/%s", self._bucket, s3_key)
        return s3_key

    def download_to_tempfile(self, s3_key: str, suffix: str = "") -> str:
        """Download an S3 object to a temporary file.

        Returns:
            Path to the temporary file. Caller is responsible for cleanup.
        """
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        self._client.download_file(self._bucket, s3_key, tmp.name)
        tmp.close()
        logger.debug("Downloaded s3://%s/%s → %s", self._bucket, s3_key, tmp.name)
        return tmp.name

    def download_bytes(self, s3_key: str) -> bytes:
        """Download an S3 object as bytes."""
        response = self._client.get_object(Bucket=self._bucket, Key=s3_key)
        return response["Body"].read()

    def exists(self, s3_key: str) -> bool:
        """Check if an object exists in S3."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_metadata(self, s3_key: str) -> dict:
        """Get object metadata (size, content_type, last_modified)."""
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=s3_key)
            return {
                "size_bytes": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", ""),
                "last_modified": str(response.get("LastModified", "")),
                "etag": response.get("ETag", ""),
            }
        except ClientError:
            return {}

    def generate_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for temporary access to an S3 object.

        Args:
            s3_key: The object key.
            expires_in: URL expiry in seconds (default 1 hour).

        Returns:
            Presigned URL string.
        """
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    def delete(self, s3_key: str) -> None:
        """Delete an object from S3."""
        self._client.delete_object(Bucket=self._bucket, Key=s3_key)

    def list_objects(self, prefix: str, max_keys: int = 100) -> list[dict]:
        """List objects with a given prefix."""
        response = self._client.list_objects_v2(
            Bucket=self._bucket, Prefix=prefix, MaxKeys=max_keys
        )
        return [
            {"key": obj["Key"], "size": obj["Size"], "last_modified": str(obj["LastModified"])}
            for obj in response.get("Contents", [])
        ]


# Module-level singleton — lazy init
_storage: StorageService | None = None


def get_storage() -> StorageService:
    """Get the global StorageService instance."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
