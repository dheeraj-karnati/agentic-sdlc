"""Enterprise file classifier for D1: Ingest.

Classifies files by ROLE (controller, service, entity, etc.) using path patterns
and assigns priority tiers for LLM analysis. No LLM needed — pure rule-based.

Supports: Java, COBOL, PL/SQL, Progress 4GL, VB6/ASP, Python, JS/TS, C#, Go, Ruby.
"""

import enum
import logging
import re
from pathlib import PurePosixPath

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FileRole(enum.StrEnum):
    """Role of a file within an enterprise codebase."""

    CONTROLLER = "controller"
    SERVICE = "service"
    ENTITY = "entity"
    REPOSITORY = "repository"
    CONFIG = "config"
    MIGRATION = "migration"
    TEST = "test"
    DTO = "dto"
    UTIL = "util"
    GENERATED = "generated"
    BUILD_FILE = "build_file"
    DOCUMENTATION = "documentation"
    STORED_PROCEDURE = "stored_procedure"
    COPYBOOK = "copybook"
    JCL = "jcl"
    VIEW = "view"
    UNKNOWN = "unknown"


class AnalysisTier(int, enum.Enum):
    """Priority tier for LLM analysis."""

    TIER_1 = 1  # Individual LLM call per file
    TIER_2 = 2  # Group-level LLM call
    TIER_3 = 3  # No LLM — classify and count only


# Roles assigned to each tier
_TIER_MAP: dict[FileRole, AnalysisTier] = {
    FileRole.CONTROLLER: AnalysisTier.TIER_1,
    FileRole.SERVICE: AnalysisTier.TIER_1,
    FileRole.CONFIG: AnalysisTier.TIER_1,
    FileRole.DOCUMENTATION: AnalysisTier.TIER_1,
    FileRole.STORED_PROCEDURE: AnalysisTier.TIER_1,
    FileRole.ENTITY: AnalysisTier.TIER_2,
    FileRole.REPOSITORY: AnalysisTier.TIER_2,
    FileRole.MIGRATION: AnalysisTier.TIER_2,
    FileRole.BUILD_FILE: AnalysisTier.TIER_2,
    FileRole.COPYBOOK: AnalysisTier.TIER_2,
    FileRole.JCL: AnalysisTier.TIER_2,
    FileRole.VIEW: AnalysisTier.TIER_2,
    FileRole.UNKNOWN: AnalysisTier.TIER_2,
    FileRole.TEST: AnalysisTier.TIER_3,
    FileRole.DTO: AnalysisTier.TIER_3,
    FileRole.UTIL: AnalysisTier.TIER_3,
    FileRole.GENERATED: AnalysisTier.TIER_3,
}


class ClassifiedFile(BaseModel):
    """Result of classifying a single file."""

    filename: str
    relative_path: str
    role: FileRole
    tier: int  # 1, 2, or 3
    language: str
    package_path: str = ""  # Java package, COBOL program, etc.
    group_key: str = ""  # for grouping (e.g., "com.acme.billing")


# ─── Language detection ───

_LANGUAGE_MAP: dict[str, str] = {
    ".java": "java",
    ".kt": "kotlin",
    ".scala": "scala",
    ".groovy": "groovy",
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c_header",
    ".hpp": "cpp_header",
    ".cbl": "cobol",
    ".cob": "cobol",
    ".cpy": "cobol_copybook",
    ".jcl": "jcl",
    ".proc": "jcl",
    ".rpg": "rpg",
    ".rpgle": "rpg",
    ".clp": "rpg",
    ".p": "progress_4gl",
    ".w": "progress_4gl",
    ".i": "progress_include",
    ".cls": "progress_class",
    ".pls": "plsql",
    ".pks": "plsql",
    ".pkb": "plsql",
    ".trg": "plsql",
    ".fnc": "plsql",
    ".prc": "plsql",
    ".vw": "sql_view",
    ".sql": "sql",
    ".bas": "vb6",
    ".frm": "vb6",
    ".vbs": "vbscript",
    ".asp": "asp_classic",
    ".asa": "asp_classic",
    ".aspx": "aspnet",
    ".pbl": "powerbuilder",
    ".srf": "powerbuilder",
    ".srd": "powerbuilder",
    ".psr": "powerbuilder",
    ".jsp": "jsp",
    ".jspx": "jsp",
    ".xhtml": "jsf",
    ".ftl": "freemarker",
    ".vm": "velocity",
    ".xml": "xml",
    ".xsl": "xslt",
    ".xslt": "xslt",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".properties": "properties",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "config",
    ".sh": "shell",
    ".bash": "shell",
    ".bat": "batch",
    ".cmd": "batch",
    ".ps1": "powershell",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".csv": "csv",
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".pptx": "pptx",
}


# ─── Role classification rules (ordered by priority — first match wins) ───

_ROLE_RULES: list[tuple[str, FileRole]] = [
    # ── Documentation (by extension) ──
    (r"\.(?:md|rst|txt|pdf|docx?|xlsx?|pptx?|csv)$", FileRole.DOCUMENTATION),

    # ── Build files (exact names) ──
    (r"(?:^|/)(?:pom\.xml|build\.gradle|settings\.gradle|gradlew|Makefile|CMakeLists\.txt|Rakefile|Gemfile|setup\.py|setup\.cfg|pyproject\.toml|package\.json|tsconfig\.json|webpack\.config|rollup\.config|vite\.config|Cargo\.toml|go\.mod|go\.sum)$", FileRole.BUILD_FILE),

    # ── Config files ──
    (r"(?:^|/)(?:application\.[^/]+|bootstrap\.[^/]+|web\.xml|ejb-jar\.xml|weblogic[\w-]*\.xml|websphere[\w-]*\.xml|ibm-[\w-]*\.xml|jboss[\w-]*\.xml|persistence\.xml|beans\.xml|context\.xml|struts[\w-]*\.xml|log4j[\w.-]*|logback[\w.-]*|hibernate\.cfg\.xml|ehcache\.xml|\.env\.example|\.htaccess|nginx\.conf|Dockerfile|docker-compose[\w.-]*|Procfile|Vagrantfile)$", FileRole.CONFIG),
    (r"(?:^|/)(?:src/main/resources/|conf/|config/|\.config/).*\.(?:xml|properties|yml|yaml|json|ini|cfg|conf)$", FileRole.CONFIG),

    # ── Tests ──
    (r"(?:^|/)(?:test|tests|__tests__|spec|specs|testing|test-integration|test-e2e)/", FileRole.TEST),
    (r"(?:Test|Tests|Spec|_test|_spec|\.test|\.spec)\.\w+$", FileRole.TEST),
    (r"(?:^|/)test_\w+\.py$", FileRole.TEST),

    # ── Generated code ──
    (r"(?:^|/)(?:generated|gen|auto-generated|target/generated)/", FileRole.GENERATED),
    (r"_generated\.\w+$", FileRole.GENERATED),
    (r"(?:^|/)R\.java$", FileRole.GENERATED),  # Android

    # ── COBOL specifics ──
    (r"\.cpy$", FileRole.COPYBOOK),
    (r"\.(?:jcl|proc)$", FileRole.JCL),
    (r"\.(?:cbl|cob)$", FileRole.SERVICE),  # COBOL programs = business logic

    # ── PL/SQL specifics ──
    (r"\.(?:pks|pkb|pls|plb|prc|fnc|trg)$", FileRole.STORED_PROCEDURE),
    (r"\.vw$", FileRole.VIEW),

    # ── Progress 4GL specifics ──
    (r"\.i$", FileRole.COPYBOOK),  # Progress include
    (r"\.w$", FileRole.VIEW),  # Progress window
    (r"\.(?:p|cls)$", FileRole.SERVICE),  # Progress procedure/class

    # ── VB6 / Classic ASP ──
    (r"\.(?:bas|frm)$", FileRole.SERVICE),
    (r"\.(?:asp|asa)$", FileRole.CONTROLLER),

    # ── RPG ──
    (r"\.(?:rpg|rpgle|clp)$", FileRole.SERVICE),

    # ── PowerBuilder ──
    (r"\.(?:pbl|srf)$", FileRole.SERVICE),
    (r"\.(?:srd|psr)$", FileRole.VIEW),  # DataWindows / reports

    # ── SQL migrations ──
    (r"(?:^|/)(?:migration|migrations|flyway|liquibase|db/migrate|sql/|ddl/|dml/)", FileRole.MIGRATION),
    (r"V\d+__\w+\.sql$", FileRole.MIGRATION),  # Flyway naming
    (r"\.sql$", FileRole.STORED_PROCEDURE),  # default for .sql = stored proc

    # ── Java/Kotlin/Scala role patterns (path-based) ──
    (r"(?:^|/)(?:controller|controllers|rest|endpoint|endpoints|resource|resources|servlet|servlets|web|api)/", FileRole.CONTROLLER),
    (r"(?:Controller|Servlet|Resource|Endpoint|RestApi)\.\w+$", FileRole.CONTROLLER),

    (r"(?:^|/)(?:service|services|business|logic|manager|facade|handler|processor|interactor|usecase)/", FileRole.SERVICE),
    (r"(?:Service|ServiceImpl|Manager|Facade|Handler|Processor|UseCase|Interactor)\.\w+$", FileRole.SERVICE),

    (r"(?:^|/)(?:entity|entities|model|models|domain|pojo|bean|beans)/", FileRole.ENTITY),
    (r"(?:Entity|Model|Domain)\.\w+$", FileRole.ENTITY),

    (r"(?:^|/)(?:repository|repositories|dao|daos|mapper|mappers|gateway|gateways|store|stores)/", FileRole.REPOSITORY),
    (r"(?:Repository|Dao|Mapper|Gateway|Store)\.\w+$", FileRole.REPOSITORY),

    (r"(?:^|/)(?:dto|dtos|vo|vos|request|response|payload|form|forms|command|commands|event|events)/", FileRole.DTO),
    (r"(?:DTO|Dto|VO|Vo|Request|Response|Payload|Form|Command|Event)\.\w+$", FileRole.DTO),

    (r"(?:^|/)(?:util|utils|utility|utilities|helper|helpers|common|shared|lib|support|tool|tools)/", FileRole.UTIL),
    (r"(?:Utils?|Helper|Utility|Constants?|Enum)\.\w+$", FileRole.UTIL),

    # ── View templates ──
    (r"\.(?:jsp|jspx|xhtml|ftl|vm|thymeleaf|mustache|hbs|ejs|pug|jade)$", FileRole.VIEW),
    (r"(?:^|/)(?:views?|templates?|pages?|screens?|layouts?|partials?|components?)/", FileRole.VIEW),

    # ── Python role patterns ──
    (r"(?:^|/)(?:views|viewsets|routers|urls|routes)\.py$", FileRole.CONTROLLER),
    (r"(?:^|/)(?:services|tasks|workers|jobs|commands)\.py$", FileRole.SERVICE),
    (r"(?:^|/)(?:models|schemas|entities)\.py$", FileRole.ENTITY),
    (r"(?:^|/)(?:repositories|queries|crud)\.py$", FileRole.REPOSITORY),
    (r"(?:^|/)(?:serializers|forms|validators)\.py$", FileRole.DTO),
    (r"(?:^|/)(?:utils|helpers|constants|enums)\.py$", FileRole.UTIL),
    (r"(?:^|/)(?:settings|config|configuration|manage)\.py$", FileRole.CONFIG),

    # ── .NET patterns ──
    (r"(?:Controller|ApiController)\.\w+$", FileRole.CONTROLLER),
    (r"(?:^|/)(?:Services|Business|Logic)/", FileRole.SERVICE),
    (r"(?:^|/)(?:Models|Entities|Data)/.*\.\w+$", FileRole.ENTITY),
    (r"(?:^|/)(?:Repositories|DataAccess)/", FileRole.REPOSITORY),
]

# Compile patterns once
_COMPILED_RULES: list[tuple[re.Pattern, FileRole]] = [
    (re.compile(pattern, re.IGNORECASE), role)
    for pattern, role in _ROLE_RULES
]


def _detect_language(filename: str) -> str:
    """Detect programming language from file extension."""
    ext = PurePosixPath(filename).suffix.lower()
    return _LANGUAGE_MAP.get(ext, "unknown")


def _extract_package_path(relative_path: str, language: str) -> str:
    """Extract package/module path for grouping.

    Java: "src/main/java/com/acme/billing/InvoiceService.java" → "com.acme.billing"
    Python: "app/services/billing.py" → "app.services"
    COBOL: "src/programs/BILLING.cbl" → "programs"
    """
    parts = PurePosixPath(relative_path).parts

    if language == "java":
        # Find the Java source root and extract package from path
        try:
            # Standard Maven/Gradle: src/main/java/com/acme/...
            for marker in ("java", "scala", "kotlin", "groovy"):
                if marker in parts:
                    idx = parts.index(marker)
                    pkg_parts = parts[idx + 1 : -1]  # exclude filename
                    return ".".join(pkg_parts)
        except (ValueError, IndexError):
            pass
        # Fallback: use parent directories, excluding common roots
        skip = {"src", "main", "java", "test", "resources"}
        pkg_parts = [p for p in parts[:-1] if p.lower() not in skip]
        return ".".join(pkg_parts[-4:])  # last 4 levels max

    if language == "python":
        return ".".join(parts[:-1])

    if language in ("cobol", "cobol_copybook", "jcl"):
        # Use parent directory
        return str(PurePosixPath(relative_path).parent)

    if language in ("plsql", "sql"):
        return str(PurePosixPath(relative_path).parent)

    if language in ("progress_4gl", "progress_include", "progress_class"):
        return str(PurePosixPath(relative_path).parent)

    # Default: parent directory
    return str(PurePosixPath(relative_path).parent)


def _compute_group_key(package_path: str, language: str) -> str:
    """Compute a group key for package-level grouping.

    For Java, groups at 3 levels: "com.acme.billing.service.InvoiceService"
    → group_key = "com.acme.billing"
    """
    if not package_path:
        return "root"

    if language == "java":
        parts = package_path.split(".")
        # Group at 3 levels for deep packages, 2 for shallow
        depth = min(3, len(parts))
        return ".".join(parts[:depth])

    # For other languages, use the directory path (max 2 levels)
    parts = PurePosixPath(package_path).parts
    depth = min(2, len(parts))
    return "/".join(parts[:depth]) if parts else "root"


def classify_file(relative_path: str) -> ClassifiedFile:
    """Classify a file by role, tier, language, and group.

    Args:
        relative_path: Path within the project/archive.

    Returns:
        ClassifiedFile with role, tier, language, package, and group key.
    """
    filename = PurePosixPath(relative_path).name
    language = _detect_language(filename)

    # Match against role rules (first match wins)
    role = FileRole.UNKNOWN
    for pattern, candidate_role in _COMPILED_RULES:
        if pattern.search(relative_path):
            role = candidate_role
            break

    tier = _TIER_MAP.get(role, AnalysisTier.TIER_2).value
    package_path = _extract_package_path(relative_path, language)
    group_key = _compute_group_key(package_path, language)

    return ClassifiedFile(
        filename=filename,
        relative_path=relative_path,
        role=role,
        tier=tier,
        language=language,
        package_path=package_path,
        group_key=group_key,
    )


def classify_files(relative_paths: list[str]) -> list[ClassifiedFile]:
    """Classify multiple files. Convenience wrapper."""
    return [classify_file(p) for p in relative_paths]
