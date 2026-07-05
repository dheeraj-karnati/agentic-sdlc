"""Deep Java / Spring / EJB / WebSphere code-structure extractor for D1: Ingest.

Extracts everything the base ``_extract_java`` does (package, class, parent,
interfaces, annotations, methods, imports, SQL, hardcoded values, key comments,
dependencies, entry points) **plus** advanced enterprise patterns:

- Spring advanced annotations (@Scheduled, @Cacheable, @Retryable, etc.)
- JPA / Hibernate entity mappings, relationships, named queries
- EJB lifecycle and concurrency annotations
- WebSphere / WebLogic JNDI and descriptor patterns
- Servlet hierarchy and filters
- Spring Security authorization annotations
- Custom exception classes
- Inner classes and enums
- Spring Batch step-scoped beans
- Method-level @Transactional with propagation/isolation

All extraction is regex-based — no external AST libraries are required.
"""

from __future__ import annotations

import re

from src.agents.ingest.skills.code_structure_skill import (
    CodeStructure,
    HardcodedValue,
    MethodSignature,
)

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

_PACKAGE_RE = re.compile(r"package\s+([\w.]+)\s*;")
_IMPORT_RE = re.compile(r"import\s+([\w.*]+)\s*;")

_CLASS_RE = re.compile(
    r"(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)"
    r"(?:\s+extends\s+(\w+))?"
    r"(?:\s+implements\s+([\w,\s]+))?",
)
_INTERFACE_RE = re.compile(
    r"(?:public\s+)?interface\s+(\w+)(?:\s+extends\s+([\w,\s]+))?"
)

_CLASS_ANNOT_RE = re.compile(
    r"@(\w+(?:\([^)]*\))?)\s*\n(?:\s*@\w+(?:\([^)]*\))?\s*\n)*"
    r"\s*(?:public\s+|abstract\s+|final\s+)*(?:class|interface|enum)\s"
)

_METHOD_RE = re.compile(
    r"((?:@\w+(?:\([^)]*\))?[ \t]*\n\s*)*)"
    r"(?:public|protected|private)\s+"
    r"(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:abstract\s+)?"
    r"([\w<>\[\],\s?]+?)\s+(\w+)\s*\(([^)]*)\)",
)

_SQL_LITERAL_RE = re.compile(
    r'["\'](\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s[^"\']{10,})["\']',
    re.IGNORECASE,
)
_SQL_CONCAT_RE = re.compile(
    r"(?:SELECT|INSERT|UPDATE|DELETE)\s+.*?\+\s*\w+", re.IGNORECASE
)

_HARDCODED_RE = re.compile(
    r"(?:static\s+)?(?:final\s+)?\w+\s+(\w+)\s*=\s*(\d{3,}|\"[^\"]{5,50}\")"
)

_KEY_COMMENT_RE = re.compile(
    r"(?://|/\*)\s*(TODO|FIXME|HACK|XXX|BUSINESS\s*RULE|IMPORTANT)[:\s]*(.*?)(?:\*/|\n)",
    re.IGNORECASE,
)

_DEP_FIELD_RE = re.compile(r"private\s+(?:final\s+)?(\w+)\s+(\w+)\s*;")

_ENDPOINT_MAPPING_RE = re.compile(
    r"@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping"
    r"|PatchMapping)\s*\(\s*(?:value\s*=\s*)?[\"']([^\"']+)",
)

# Spring advanced
_SCHEDULED_RE = re.compile(
    r"@Scheduled\s*\(([^)]*)\)", re.DOTALL
)
_SPRING_ADV_CLASS_RE = re.compile(
    r"@(Cacheable|Retryable|CircuitBreaker|Async|EventListener)"
    r"(?:\([^)]*\))?\s*\n\s*(?:public|protected|private)"
)

# JPA / Hibernate
_ENTITY_TABLE_RE = re.compile(
    r'@Table\s*\(\s*name\s*=\s*["\']([^"\']+)["\']'
)
_COLUMN_RE = re.compile(
    r'@Column\s*\(\s*name\s*=\s*["\']([^"\']+)["\']'
)
_JPA_RELATIONSHIP_RE = re.compile(
    r"@(OneToMany|ManyToOne|ManyToMany|OneToOne)(?:\([^)]*\))?"
)
_NAMED_QUERY_RE = re.compile(
    r'@NamedQuery\s*\(\s*name\s*=\s*["\']([^"\']+)["\']'
    r'\s*,\s*query\s*=\s*["\']([^"\']+)["\']',
)
_QUERY_ANNOT_RE = re.compile(
    r'@Query\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
)

# EJB
_EJB_ANNOT_RE = re.compile(
    r"@(Stateless|Stateful|MessageDriven|Singleton|PostConstruct"
    r"|PreDestroy|Timeout|Schedule)\b"
)
_EJB_SCHEDULE_RE = re.compile(
    r"@Schedule\s*\(([^)]*)\)", re.DOTALL
)

# WebSphere / WebLogic / JNDI
_JNDI_LOOKUP_RE = re.compile(
    r'(?:InitialContext|lookup)\s*\(\s*["\']([^"\']*)["\']'
)
_RESOURCE_REF_RE = re.compile(
    r'@Resource(?:Ref)?\s*\(\s*(?:name\s*=\s*)?["\']([^"\']+)["\']'
)
_IBM_WEB_BND_RE = re.compile(r"ibm-web-bnd", re.IGNORECASE)
_WEBLOGIC_RE = re.compile(r"weblogic\.xml|weblogic\.application", re.IGNORECASE)

# Servlet
_SERVLET_EXTEND_RE = re.compile(
    r"class\s+(\w+)\s+extends\s+HttpServlet"
)
_WEB_FILTER_RE = re.compile(
    r"@WebFilter\s*\(\s*(?:urlPatterns\s*=\s*)?[\"']([^\"']+)[\"']"
)
_WEB_SERVLET_RE = re.compile(
    r"@WebServlet\s*\(\s*(?:urlPatterns\s*=\s*|value\s*=\s*)?[\"']([^\"']+)[\"']"
)
_FILTER_CHAIN_RE = re.compile(
    r"(?:implements\s+[\w,\s]*Filter|FilterChain)"
)

# Spring Security
_SECURITY_ANNOT_RE = re.compile(
    r'@(PreAuthorize|Secured|RolesAllowed)\s*\(\s*["\']?([^)"\']+)["\']?\s*\)'
)
_SECURITY_FILTER_CHAIN_RE = re.compile(r"SecurityFilterChain|AuthenticationManager")

# Exception classes
_EXCEPTION_CLASS_RE = re.compile(
    r"class\s+(\w+)\s+extends\s+(\w*(?:Exception|Error|Throwable))"
)

# Inner classes
_INNER_CLASS_RE = re.compile(
    r"(?:public|protected|private)\s+(static\s+)?class\s+(\w+)"
)

# Enum classes
_ENUM_RE = re.compile(
    r"(?:public\s+)?enum\s+(\w+)\s*\{([^}]*)\}",
    re.DOTALL,
)

# Spring Batch
_STEP_SCOPE_RE = re.compile(r"@StepScope")
_BATCH_IFACE_RE = re.compile(
    r"implements\s+[\w,\s]*(ItemReader|ItemWriter|ItemProcessor)"
)

# @Transactional with attributes
_TRANSACTIONAL_RE = re.compile(
    r"@Transactional\s*\(([^)]+)\)", re.DOTALL
)

# @Value with defaults
_VALUE_ANNOT_RE = re.compile(
    r'@Value\s*\(\s*["\']\$\{([^}]+):([^}"\']+)\}["\']'
)

# @Autowired field injection
_AUTOWIRED_FIELD_RE = re.compile(
    r"@Autowired\s+(?:private|protected|public)\s+(\w+)\s+\w+\s*;"
)

# Constructor injection (multi-param)
_CONSTRUCTOR_PARAM_RE = re.compile(
    r"(?:public|protected)\s+\w+\s*\(((?:\s*(?:final\s+)?[\w<>,\s]+\s+\w+\s*,?\s*)+)\)"
)

# Primitives / wrappers to exclude from dependency detection
_NON_DEP_TYPES: frozenset[str] = frozenset({
    "String", "Integer", "Long", "Boolean", "Double", "Float", "Short",
    "Byte", "Character", "BigDecimal", "BigInteger", "List", "Map",
    "Set", "Optional", "Object", "void", "int", "long", "boolean",
    "double", "float", "short", "byte", "char",
})


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _dedupe(items: list[str]) -> list[str]:
    """De-duplicate a list while preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _is_bean_type(name: str) -> bool:
    """Return *True* if *name* looks like a user-defined bean type."""
    return bool(name) and name[0].isupper() and name not in _NON_DEP_TYPES


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------


def extract(content: str, file_path: str) -> CodeStructure:
    """Extract deep Java / Spring / EJB / WebSphere code structure.

    This function is a drop-in replacement for the basic ``_extract_java``
    in ``code_structure_skill.py``.  It covers the same baseline extractions
    **plus** advanced enterprise Java patterns.

    Args:
        content: Full source-code text of a ``.java`` file.
        file_path: Relative or absolute path to the file (used for context).

    Returns:
        A fully populated :class:`CodeStructure` instance.
    """
    cs = CodeStructure(language="java", file_path=file_path)

    # ── Package ──────────────────────────────────────────────────────────
    m = _PACKAGE_RE.search(content)
    if m:
        cs.package = m.group(1)

    # ── Imports ──────────────────────────────────────────────────────────
    cs.imports = _IMPORT_RE.findall(content)

    # ── Class / interface declaration ────────────────────────────────────
    m = _CLASS_RE.search(content)
    if m:
        cs.class_name = m.group(1)
        cs.parent_class = m.group(2) or ""
        if m.group(3):
            cs.interfaces = [i.strip() for i in m.group(3).split(",")]

    if not cs.class_name:
        m = _INTERFACE_RE.search(content)
        if m:
            cs.class_name = m.group(1)
            if m.group(2):
                cs.interfaces = [i.strip() for i in m.group(2).split(",")]

    # ── Enum class (top-level) ───────────────────────────────────────────
    if not cs.class_name:
        em = _ENUM_RE.search(content)
        if em:
            cs.class_name = em.group(1)
            values_raw = em.group(2).strip()
            # Grab comma-separated identifiers before any '(' or '{'
            enum_values = re.findall(r"(\w+)\s*(?:\(|,|;|$)", values_raw)
            if enum_values:
                cs.key_comments.append(
                    f"Enum {em.group(1)} values: {', '.join(enum_values[:30])}"
                )

    # ── Class-level annotations ──────────────────────────────────────────
    class_annots: list[str] = []
    for am in _CLASS_ANNOT_RE.finditer(content):
        # The first capture group may span multiple annotation lines; take
        # only the annotation name (strip arguments).
        raw = am.group(1)
        name = raw.split("(")[0].lstrip("@")
        class_annots.append(name)
    # Fallback: simpler single-line scan (matches the original logic)
    for am in re.finditer(
        r"@(\w+)(?:\([^)]*\))?\s*(?:public|abstract|final|class|interface|enum)",
        content,
    ):
        class_annots.append(am.group(1))
    cs.annotations = _dedupe(class_annots)

    # ── Methods ──────────────────────────────────────────────────────────
    for mm in _METHOD_RE.finditer(content):
        annot_block: str = mm.group(1)
        ret: str = mm.group(2).strip()
        name: str = mm.group(3)
        params: str = mm.group(4).strip()
        ms = MethodSignature(name=name, params=params, return_type=ret)
        if annot_block:
            ms.annotations = [
                a.split("(")[0]
                for a in re.findall(r"@(\w+(?:\([^)]*\))?)", annot_block)
            ]
        cs.methods.append(ms)

    # ── Embedded SQL ─────────────────────────────────────────────────────
    cs.sql_queries = [s.strip() for s in _SQL_LITERAL_RE.findall(content)][:20]
    cs.sql_queries.extend(
        s.strip()[:200] for s in _SQL_CONCAT_RE.findall(content)[:10]
    )

    # ── Hardcoded values (numeric / string constants) ────────────────────
    for hm in _HARDCODED_RE.finditer(content):
        cs.hardcoded_values.append(
            HardcodedValue(name=hm.group(1), value=hm.group(2))
        )

    # ── Key comments (TODO, FIXME, HACK, BUSINESS RULE, …) ──────────────
    for cm in _KEY_COMMENT_RE.finditer(content):
        cs.key_comments.append(f"{cm.group(1)}: {cm.group(2).strip()}"[:200])

    # ── Dependencies — field injection (@Autowired) ──────────────────────
    for dm in _AUTOWIRED_FIELD_RE.finditer(content):
        dep = dm.group(1)
        if _is_bean_type(dep):
            cs.dependencies.append(dep)

    # ── Dependencies — private final fields (constructor injection) ──────
    for dm in _DEP_FIELD_RE.finditer(content):
        dep = dm.group(1)
        if _is_bean_type(dep):
            cs.dependencies.append(dep)

    # ── Dependencies — constructor parameter types ───────────────────────
    for cm in _CONSTRUCTOR_PARAM_RE.finditer(content):
        for pm in re.finditer(r"(?:final\s+)?([\w<>]+)\s+\w+", cm.group(1)):
            raw_type = pm.group(1).split("<")[0]
            if _is_bean_type(raw_type):
                cs.dependencies.append(raw_type)

    cs.dependencies = _dedupe(cs.dependencies)

    # ── Entry points — REST endpoints ────────────────────────────────────
    if any(
        a in cs.annotations
        for a in ("RestController", "Controller", "WebServlet")
    ):
        cs.entry_points.append(f"HTTP endpoint: {cs.class_name}")
    for em in _ENDPOINT_MAPPING_RE.finditer(content):
        cs.entry_points.append(f"Endpoint: {em.group(1)}")

    # ==================================================================
    # ENTERPRISE JAVA EXTENSIONS
    # ==================================================================

    # ── 1. Spring @Scheduled ─────────────────────────────────────────────
    for sm in _SCHEDULED_RE.finditer(content):
        cron_match = re.search(r'cron\s*=\s*["\']([^"\']+)["\']', sm.group(1))
        if cron_match:
            expr = cron_match.group(1)
            cs.entry_points.append(f"@Scheduled cron: {expr}")
            cs.key_comments.append(f"Scheduled cron expression: {expr}")
        else:
            cs.entry_points.append(f"@Scheduled({sm.group(1).strip()})")

    # ── 2. Spring advanced method annotations ────────────────────────────
    for sam in _SPRING_ADV_CLASS_RE.finditer(content):
        cs.annotations.append(sam.group(1))
    cs.annotations = _dedupe(cs.annotations)

    # ── 3. JPA / Hibernate — @Entity + @Table ────────────────────────────
    if re.search(r"@Entity\b", content):
        cs.annotations.append("Entity")
        tm = _ENTITY_TABLE_RE.search(content)
        if tm:
            cs.key_comments.append(f"JPA @Table name: {tm.group(1)}")

    # @Column mappings
    for col in _COLUMN_RE.finditer(content):
        cs.key_comments.append(f"@Column: {col.group(1)}")

    # Relationships
    for rm in _JPA_RELATIONSHIP_RE.finditer(content):
        cs.annotations.append(rm.group(1))
    cs.annotations = _dedupe(cs.annotations)

    # @NamedQuery
    for nq in _NAMED_QUERY_RE.finditer(content):
        cs.key_comments.append(f"@NamedQuery {nq.group(1)}: {nq.group(2)[:150]}")

    # @Query (HQL / JPQL)
    for qq in _QUERY_ANNOT_RE.finditer(content):
        query_text = qq.group(1).strip()[:200]
        cs.sql_queries.append(query_text)
        cs.key_comments.append(f"@Query HQL/JPQL: {query_text}")

    # ── 4. EJB annotations ──────────────────────────────────────────────
    ejb_found: list[str] = _EJB_ANNOT_RE.findall(content)
    if ejb_found:
        cs.annotations.append("EJB")
        for ejb_name in ejb_found:
            cs.annotations.append(ejb_name)
    cs.annotations = _dedupe(cs.annotations)

    # @MessageDriven → entry point
    if "MessageDriven" in cs.annotations:
        cs.entry_points.append(f"@MessageDriven: {cs.class_name}")

    # @Schedule with EJB timer
    for es in _EJB_SCHEDULE_RE.finditer(content):
        cs.key_comments.append(f"EJB @Schedule: {es.group(1).strip()[:150]}")
        cs.entry_points.append("EJB @Schedule timer")

    # ── 5. WebSphere / WebLogic / JNDI ───────────────────────────────────
    for jm in _JNDI_LOOKUP_RE.finditer(content):
        lookup_name = jm.group(1)
        cs.entry_points.append(f"JNDI lookup: {lookup_name}")
        cs.dependencies.append(f"JNDI:{lookup_name}")

    for rr in _RESOURCE_REF_RE.finditer(content):
        cs.dependencies.append(f"@Resource: {rr.group(1)}")

    if _IBM_WEB_BND_RE.search(content):
        cs.key_comments.append("IBM WebSphere ibm-web-bnd binding detected")

    if _WEBLOGIC_RE.search(content):
        cs.key_comments.append("WebLogic descriptor pattern detected")

    # ── 6. Servlet patterns ──────────────────────────────────────────────
    sm = _SERVLET_EXTEND_RE.search(content)
    if sm:
        cs.entry_points.append(f"HttpServlet: {sm.group(1)}")

    # doGet / doPost detection
    for http_method in ("doGet", "doPost", "doPut", "doDelete", "service"):
        if re.search(rf"\b{http_method}\s*\(", content):
            cs.entry_points.append(f"Servlet method: {http_method}")

    for wf in _WEB_FILTER_RE.finditer(content):
        cs.entry_points.append(f"@WebFilter: {wf.group(1)}")

    for ws in _WEB_SERVLET_RE.finditer(content):
        cs.entry_points.append(f"@WebServlet: {ws.group(1)}")

    if _FILTER_CHAIN_RE.search(content):
        cs.annotations.append("Filter")
        cs.annotations = _dedupe(cs.annotations)

    # ── 7. Spring Security ───────────────────────────────────────────────
    for sec in _SECURITY_ANNOT_RE.finditer(content):
        cs.key_comments.append(f"@{sec.group(1)}: {sec.group(2).strip()[:100]}")

    if _SECURITY_FILTER_CHAIN_RE.search(content):
        cs.annotations.append("SecurityConfig")
        cs.annotations = _dedupe(cs.annotations)

    # ── 8. Custom exception classes ──────────────────────────────────────
    for exc in _EXCEPTION_CLASS_RE.finditer(content):
        cs.key_comments.append(
            f"Business exception: {exc.group(1)} extends {exc.group(2)}"
        )

    # ── 9. Inner classes ─────────────────────────────────────────────────
    # Skip the first match if it's the outer class itself.
    inner_matches = list(_INNER_CLASS_RE.finditer(content))
    for idx, ic in enumerate(inner_matches):
        # The very first class declaration is the outer class — skip it.
        if idx == 0 and ic.group(2) == cs.class_name:
            continue
        kind = "static inner" if ic.group(1) else "inner"
        cs.key_comments.append(f"{kind.capitalize()} class: {ic.group(2)}")

    # ── 10. Enum classes (nested) ────────────────────────────────────────
    for em in _ENUM_RE.finditer(content):
        enum_name = em.group(1)
        if enum_name == cs.class_name:
            continue  # already captured as top-level enum
        values_raw = em.group(2).strip()
        enum_values = re.findall(r"(\w+)\s*(?:\(|,|;|$)", values_raw)
        if enum_values:
            cs.key_comments.append(
                f"Enum {enum_name} values: {', '.join(enum_values[:30])}"
            )

    # ── 11. Spring Batch ─────────────────────────────────────────────────
    if _STEP_SCOPE_RE.search(content):
        cs.annotations.append("StepScope")
        cs.annotations = _dedupe(cs.annotations)

    for bm in _BATCH_IFACE_RE.finditer(content):
        cs.interfaces.append(bm.group(1))
    cs.interfaces = _dedupe(cs.interfaces)

    # ── 12. @Transactional with propagation / isolation ──────────────────
    for tm in _TRANSACTIONAL_RE.finditer(content):
        attrs = tm.group(1).strip()[:150]
        cs.key_comments.append(f"@Transactional({attrs})")

    # ── 13. @Value defaults (hardcoded fallback values) ──────────────────
    for vm in _VALUE_ANNOT_RE.finditer(content):
        cs.hardcoded_values.append(
            HardcodedValue(
                name=f"@Value ${{{vm.group(1)}}}",
                value=vm.group(2),
                line_hint="Spring @Value default",
            )
        )

    # ── Final de-duplication ─────────────────────────────────────────────
    cs.dependencies = _dedupe(cs.dependencies)
    cs.entry_points = _dedupe(cs.entry_points)
    cs.key_comments = _dedupe(cs.key_comments)

    return cs
