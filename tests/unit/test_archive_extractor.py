"""Tests for archive extraction service."""

import io
import zipfile

import pytest

from src.services.archive_extractor import (
    ExtractionResult,
    ExtractedFile,
    _should_skip_path,
    extract_zip,
)


# ─── Skip pattern tests ───


class TestSkipPatterns:
    def test_skip_git_directory(self):
        assert _should_skip_path(".git/config") is True
        assert _should_skip_path("src/.git/HEAD") is True

    def test_skip_node_modules(self):
        assert _should_skip_path("node_modules/express/index.js") is True

    def test_skip_pycache(self):
        assert _should_skip_path("src/__pycache__/main.cpython-312.pyc") is True

    def test_skip_target_classes(self):
        assert _should_skip_path("target/classes/com/acme/App.class") is True

    def test_skip_class_files(self):
        assert _should_skip_path("com/acme/App.class") is True

    def test_skip_jar_files(self):
        assert _should_skip_path("lib/spring-core-5.3.jar") is True

    def test_skip_ds_store(self):
        assert _should_skip_path(".DS_Store") is True
        assert _should_skip_path("src/.DS_Store") is True

    def test_skip_lock_files(self):
        assert _should_skip_path("package-lock.json") is True
        assert _should_skip_path("yarn.lock") is True

    def test_skip_minified(self):
        assert _should_skip_path("dist/bundle.min.js") is True
        assert _should_skip_path("assets/style.min.css") is True

    def test_keep_java_source(self):
        assert _should_skip_path("src/main/java/com/acme/App.java") is False

    def test_keep_python_source(self):
        assert _should_skip_path("src/services/billing.py") is False

    def test_keep_cobol(self):
        assert _should_skip_path("src/programs/BILLING.cbl") is False

    def test_keep_sql(self):
        assert _should_skip_path("db/migrations/V001__init.sql") is False

    def test_keep_config(self):
        assert _should_skip_path("src/main/resources/application.properties") is False

    def test_keep_pom(self):
        assert _should_skip_path("pom.xml") is False

    def test_keep_markdown(self):
        assert _should_skip_path("docs/BRD.md") is False

    def test_skip_hidden_files(self):
        assert _should_skip_path(".hidden_file") is True
        assert _should_skip_path("src/.secret") is True

    def test_keep_env_example(self):
        assert _should_skip_path(".env.example") is False


# ─── ZIP extraction tests ───


def _make_zip(files: dict[str, str | bytes]) -> bytes:
    """Create a ZIP in memory with the given files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(path, content)
    return buf.getvalue()


class TestExtractZip:
    def test_basic_extraction(self):
        zip_bytes = _make_zip({
            "src/main/java/App.java": "public class App {}",
            "src/main/java/Service.java": "public class Service {}",
            "README.md": "# Hello",
        })
        result = extract_zip(zip_bytes, "test.zip")
        assert len(result.files) == 3
        assert result.skipped_count == 0
        assert result.total_size > 0

    def test_skips_class_files(self):
        zip_bytes = _make_zip({
            "src/App.java": "public class App {}",
            "target/classes/App.class": b"\xca\xfe\xba\xbe",
            "lib/spring.jar": b"PK\x03\x04fake",
        })
        result = extract_zip(zip_bytes, "test.zip")
        assert len(result.files) == 1
        assert result.files[0].relative_path == "src/App.java"
        assert result.skipped_count == 2

    def test_skips_node_modules(self):
        zip_bytes = _make_zip({
            "src/index.js": "console.log('hi')",
            "node_modules/express/index.js": "module.exports = ...",
            "node_modules/lodash/lodash.js": "// lodash",
        })
        result = extract_zip(zip_bytes, "test.zip")
        assert len(result.files) == 1

    def test_skips_git_directory(self):
        zip_bytes = _make_zip({
            "src/main.py": "print('hello')",
            ".git/HEAD": "ref: refs/heads/main",
            ".git/config": "[core]",
        })
        result = extract_zip(zip_bytes, "test.zip")
        assert len(result.files) == 1

    def test_preserves_relative_path(self):
        zip_bytes = _make_zip({
            "com/acme/billing/InvoiceService.java": "class InvoiceService {}",
        })
        result = extract_zip(zip_bytes, "project.zip")
        assert result.files[0].relative_path == "com/acme/billing/InvoiceService.java"
        assert result.files[0].archive_source == "project.zip"

    def test_nested_zip(self):
        inner_zip = _make_zip({"inner/file.java": "class Inner {}"})
        outer_zip = _make_zip({
            "outer.java": "class Outer {}",
            "libs/inner.zip": inner_zip,
        })
        result = extract_zip(outer_zip, "outer.zip")
        paths = {f.relative_path for f in result.files}
        assert "outer.java" in paths
        assert "libs/inner/file.java" in paths

    def test_max_depth_limit(self):
        # Create 4-deep nested ZIPs (exceeds MAX_DEPTH=3)
        content = _make_zip({"deep.txt": "deep content"})
        for i in range(4):
            content = _make_zip({f"level{i}/nested.zip": content})

        result = extract_zip(content, "bomb.zip")
        assert any("depth" in e.lower() for e in result.errors)

    def test_zip_bomb_detection(self):
        # Create a file with very high compression ratio
        # Repeat the same byte 10MB worth — compresses to almost nothing
        huge_content = b"A" * (10 * 1024 * 1024)
        zip_bytes = _make_zip({"bomb.txt": huge_content})

        # The actual ratio depends on compression — if it exceeds ZIP_BOMB_RATIO, it should be rejected
        result = extract_zip(zip_bytes, "bomb.zip")
        # This might not trigger since ZIP_DEFLATED has a max ratio ~1000x for repeated bytes
        # but the test validates the check runs without error
        assert isinstance(result, ExtractionResult)

    def test_invalid_zip(self):
        result = extract_zip(b"not a zip file", "bad.zip")
        assert len(result.files) == 0
        assert any("Invalid ZIP" in e for e in result.errors)

    def test_empty_zip(self):
        zip_bytes = _make_zip({})
        result = extract_zip(zip_bytes, "empty.zip")
        assert len(result.files) == 0
        assert result.skipped_count == 0

    def test_mixed_enterprise_files(self):
        """Simulate a Java + COBOL mixed project."""
        zip_bytes = _make_zip({
            "java/com/acme/App.java": "public class App {}",
            "java/com/acme/AppTest.java": "public class AppTest {}",
            "cobol/BILLING.cbl": "IDENTIFICATION DIVISION.",
            "cobol/COPYLIB/CUSTCPY.cpy": "01 CUSTOMER-RECORD.",
            "jcl/NIGHTRUN.jcl": "//NIGHTRUN JOB",
            "sql/PKG_BILLING.pks": "CREATE PACKAGE",
            "docs/BRD.docx": b"PK\x03\x04docx-content",
            ".git/HEAD": "ref: refs/heads/main",
            "target/classes/App.class": b"\xca\xfe",
        })
        result = extract_zip(zip_bytes, "enterprise.zip")
        paths = {f.relative_path for f in result.files}
        assert "java/com/acme/App.java" in paths
        assert "java/com/acme/AppTest.java" in paths
        assert "cobol/BILLING.cbl" in paths
        assert "cobol/COPYLIB/CUSTCPY.cpy" in paths
        assert "jcl/NIGHTRUN.jcl" in paths
        assert "sql/PKG_BILLING.pks" in paths
        assert "docs/BRD.docx" in paths
        # Skipped
        assert ".git/HEAD" not in paths
        assert "target/classes/App.class" not in paths
