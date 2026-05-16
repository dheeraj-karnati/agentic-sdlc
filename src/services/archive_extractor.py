"""Archive extraction service for ZIP and TAR files.

Safely extracts archive contents at upload time, filtering out junk files
(compiled classes, node_modules, .git, etc.) and protecting against zip bombs.
Creates individual files for downstream Artifact record creation.
"""

import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

logger = logging.getLogger(__name__)

# ─── Safety limits ───

MAX_EXTRACT_SIZE: int = 500_000_000  # 500 MB total extracted
MAX_FILE_COUNT: int = 5_000
MAX_SINGLE_FILE: int = 50_000_000  # 50 MB per file
MAX_DEPTH: int = 3  # nested ZIP recursion limit
ZIP_BOMB_RATIO: int = 100  # reject if compressed-to-uncompressed > 100x

# ─── Skip patterns ───

SKIP_DIRECTORIES: set[str] = {
    ".git", ".svn", ".hg", ".bzr",
    "node_modules", "bower_components",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "target/classes", "target/test-classes", "target/generated-sources",
    "bin/Debug", "bin/Release", "obj",
    ".gradle", ".mvn", "build/classes", "build/generated",
    ".idea", ".vscode", ".settings", ".project",
    ".next", ".nuxt", "dist", "out",
    "vendor/bundle",  # Ruby
    ".tox", ".eggs",
    "coverage", "htmlcov",
}

SKIP_EXTENSIONS: set[str] = {
    # Compiled / binary
    ".class", ".jar", ".war", ".ear", ".aar",
    ".o", ".obj", ".exe", ".dll", ".so", ".dylib", ".a", ".lib",
    ".pyc", ".pyo", ".pyd", ".whl", ".egg",
    # Minified / maps
    ".min.js", ".min.css", ".map",
    # Lock files
    ".lock",
    # Archives within archives (handled by recursion, not as individual files)
    # Images (not useful as code)
    ".ico", ".cur",
    # Databases
    ".db", ".sqlite", ".sqlite3", ".mdb",
}

SKIP_FILENAMES: set[str] = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
    ".gitignore", ".gitattributes", ".gitmodules",
    ".npmrc", ".yarnrc", ".editorconfig",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Gemfile.lock", "Pipfile.lock", "poetry.lock",
}

# Extensions that are nested archives we should recurse into
ARCHIVE_EXTENSIONS: set[str] = {".zip"}


@dataclass
class ExtractedFile:
    """A single file extracted from an archive."""

    relative_path: str  # path within the archive (e.g., "src/main/java/com/acme/App.java")
    content: bytes  # raw file bytes
    size_bytes: int
    archive_source: str  # original archive filename


@dataclass
class ExtractionResult:
    """Result of extracting an archive."""

    files: list[ExtractedFile] = field(default_factory=list)
    skipped_count: int = 0
    total_size: int = 0
    errors: list[str] = field(default_factory=list)


def _should_skip_path(relative_path: str) -> bool:
    """Check if a file path should be skipped based on directory/extension/filename rules."""
    parts = PurePosixPath(relative_path).parts

    # Skip if any directory component matches
    for part in parts[:-1]:  # all except filename
        if part in SKIP_DIRECTORIES:
            return True
        # Also skip directories that start with a skip pattern (e.g., "target/classes/com")
        for skip_dir in SKIP_DIRECTORIES:
            if "/" in skip_dir:
                # Multi-level pattern like "target/classes"
                joined = "/".join(parts)
                if skip_dir in joined:
                    return True

    filename = parts[-1] if parts else ""

    # Skip by exact filename
    if filename in SKIP_FILENAMES:
        return True

    # Skip by extension
    ext = Path(filename).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return True

    # Skip .min.js and .min.css (compound extensions)
    if filename.endswith((".min.js", ".min.css")):
        return True

    # Skip hidden files (except common config files)
    return filename.startswith(".") and filename not in {".env.example", ".htaccess", ".babelrc"}


def extract_zip(
    archive_bytes: bytes,
    archive_filename: str,
    *,
    _depth: int = 0,
) -> ExtractionResult:
    """Extract a ZIP archive, recursing into nested ZIPs up to MAX_DEPTH.

    Args:
        archive_bytes: Raw bytes of the ZIP file.
        archive_filename: Original filename for traceability.
        _depth: Current recursion depth (internal use).

    Returns:
        ExtractionResult with extracted files, skip counts, and errors.
    """
    result = ExtractionResult()

    if _depth >= MAX_DEPTH:
        result.errors.append(
            f"Skipped nested archive at depth {_depth}: {archive_filename}"
        )
        return result

    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as zf:
            # ─── Zip bomb check ───
            total_compressed = sum(i.compress_size for i in zf.infolist() if not i.is_dir())
            total_uncompressed = sum(i.file_size for i in zf.infolist() if not i.is_dir())

            if total_compressed > 0 and total_uncompressed / total_compressed > ZIP_BOMB_RATIO:
                result.errors.append(
                    f"Possible zip bomb detected in {archive_filename}: "
                    f"compression ratio {total_uncompressed / total_compressed:.0f}x "
                    f"(limit: {ZIP_BOMB_RATIO}x)"
                )
                return result

            if total_uncompressed > MAX_EXTRACT_SIZE:
                result.errors.append(
                    f"Archive too large: {archive_filename} would extract to "
                    f"{total_uncompressed / 1_000_000:.0f}MB (limit: {MAX_EXTRACT_SIZE // 1_000_000}MB)"
                )
                return result

            file_count = sum(1 for i in zf.infolist() if not i.is_dir())
            if file_count > MAX_FILE_COUNT:
                result.errors.append(
                    f"Too many files in {archive_filename}: {file_count} "
                    f"(limit: {MAX_FILE_COUNT})"
                )
                return result

            # ─── Extract files ───
            for info in zf.infolist():
                if info.is_dir():
                    continue

                relative_path = info.filename

                # Normalize path separators
                relative_path = relative_path.replace("\\", "/")

                # Strip leading slashes / dots for safety
                while relative_path.startswith(("../", "./", "/")):
                    relative_path = relative_path.lstrip("./")

                if not relative_path:
                    continue

                # Skip junk files
                if _should_skip_path(relative_path):
                    result.skipped_count += 1
                    continue

                # Size check per file
                if info.file_size > MAX_SINGLE_FILE:
                    result.errors.append(
                        f"Skipped oversized file: {relative_path} "
                        f"({info.file_size / 1_000_000:.0f}MB, limit: {MAX_SINGLE_FILE // 1_000_000}MB)"
                    )
                    result.skipped_count += 1
                    continue

                # Total size check
                if result.total_size + info.file_size > MAX_EXTRACT_SIZE:
                    result.errors.append(
                        f"Total extraction size limit reached at {relative_path}"
                    )
                    break

                # File count check
                if len(result.files) >= MAX_FILE_COUNT:
                    result.errors.append(
                        f"File count limit reached ({MAX_FILE_COUNT})"
                    )
                    break

                try:
                    file_bytes = zf.read(info.filename)
                except Exception as e:
                    result.errors.append(f"Failed to read {relative_path}: {e}")
                    result.skipped_count += 1
                    continue

                # Check for nested archives
                ext = Path(relative_path).suffix.lower()
                if ext in ARCHIVE_EXTENSIONS:
                    nested = extract_zip(
                        file_bytes,
                        relative_path,
                        _depth=_depth + 1,
                    )
                    # Prefix nested file paths with parent archive path
                    parent_dir = str(PurePosixPath(relative_path).parent)
                    for nf in nested.files:
                        nf.relative_path = (
                            f"{parent_dir}/{nf.relative_path}"
                            if parent_dir != "."
                            else nf.relative_path
                        )
                        nf.archive_source = archive_filename
                    result.files.extend(nested.files)
                    result.skipped_count += nested.skipped_count
                    result.total_size += nested.total_size
                    result.errors.extend(nested.errors)
                    continue

                result.files.append(
                    ExtractedFile(
                        relative_path=relative_path,
                        content=file_bytes,
                        size_bytes=len(file_bytes),
                        archive_source=archive_filename,
                    )
                )
                result.total_size += len(file_bytes)

    except zipfile.BadZipFile:
        result.errors.append(f"Invalid ZIP file: {archive_filename}")
    except Exception as e:
        result.errors.append(f"Failed to extract {archive_filename}: {e}")

    logger.info(
        "Extracted %d files from %s (skipped %d, total %dMB, errors: %d)",
        len(result.files),
        archive_filename,
        result.skipped_count,
        result.total_size // 1_000_000,
        len(result.errors),
    )

    return result
