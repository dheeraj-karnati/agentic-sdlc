"""Package/module grouping for D1: Ingest.

Groups classified files by package (Java), directory (COBOL), or module path
for efficient batch LLM analysis. Instead of 2000 individual business_context
entries, produces ~80-150 grouped entries.

Storage strategy:
- Tier 1 files: 1 business_context entry per file (full content)
- Tier 2 files: 1 entry per package group (aggregated summaries)
- Tier 3 files: 1 summary entry (counts only)
"""

import logging
from collections import defaultdict

from pydantic import BaseModel, Field

from src.agents.ingest.skills.code_structure_skill import CodeStructure
from src.agents.ingest.skills.enterprise_classifier_skill import ClassifiedFile

logger = logging.getLogger(__name__)

MAX_GROUP_SIZE = 20  # Split groups larger than this


class GroupedFile(BaseModel):
    """A file within a package group."""

    filename: str
    relative_path: str
    role: str
    language: str
    content: str = ""  # truncated content for Tier 1, empty for grouped
    code_structure: CodeStructure | None = None


class PackageGroup(BaseModel):
    """A group of related files for batch analysis."""

    group_key: str
    language: str
    file_count: int
    tier: int  # min tier of any file in this group (1 = has high-value files)
    roles: dict[str, int] = Field(default_factory=dict)
    files: list[GroupedFile] = Field(default_factory=list)


class GroupingSummary(BaseModel):
    """Overall grouping result."""

    tier1_files: list[GroupedFile] = Field(default_factory=list)
    tier2_groups: list[PackageGroup] = Field(default_factory=list)
    tier3_summary: dict[str, int] = Field(default_factory=dict)  # role -> count
    tier3_files: list[str] = Field(default_factory=list)  # just filenames
    total_files: int = 0
    total_groups: int = 0


def group_files(
    classified_files: list[ClassifiedFile],
    file_contents: dict[str, str] | None = None,
    code_structures: dict[str, CodeStructure] | None = None,
) -> GroupingSummary:
    """Group classified files by tier and package.

    Args:
        classified_files: Files with role, tier, group_key from enterprise classifier.
        file_contents: Optional map of filename -> content for Tier 1 files.
        code_structures: Optional map of filename -> CodeStructure.

    Returns:
        GroupingSummary with tier1 individual files, tier2 package groups, tier3 counts.
    """
    contents = file_contents or {}
    structures = code_structures or {}

    result = GroupingSummary(total_files=len(classified_files))

    # Separate by tier
    tier1: list[ClassifiedFile] = []
    tier2: list[ClassifiedFile] = []
    tier3: list[ClassifiedFile] = []

    for cf in classified_files:
        if cf.tier == 1:
            tier1.append(cf)
        elif cf.tier == 2:
            tier2.append(cf)
        else:
            tier3.append(cf)

    # ─── Tier 1: individual entries ───
    for cf in tier1:
        gf = GroupedFile(
            filename=cf.filename,
            relative_path=cf.relative_path,
            role=cf.role.value,
            language=cf.language,
            content=contents.get(cf.filename, contents.get(cf.relative_path, "")),
            code_structure=structures.get(cf.filename, structures.get(cf.relative_path)),
        )
        result.tier1_files.append(gf)

    # ─── Tier 2: group by package ───
    groups: dict[str, list[ClassifiedFile]] = defaultdict(list)
    for cf in tier2:
        groups[cf.group_key].append(cf)

    for group_key, files in groups.items():
        # Split large groups
        chunks = [files[i:i + MAX_GROUP_SIZE] for i in range(0, len(files), MAX_GROUP_SIZE)]

        for chunk_idx, chunk in enumerate(chunks):
            key = f"{group_key}#{chunk_idx}" if len(chunks) > 1 else group_key

            # Compute role counts
            role_counts: dict[str, int] = {}
            for cf in chunk:
                role_counts[cf.role.value] = role_counts.get(cf.role.value, 0) + 1

            # Determine dominant language
            lang_counts: dict[str, int] = {}
            for cf in chunk:
                lang_counts[cf.language] = lang_counts.get(cf.language, 0) + 1
            dominant_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "unknown"

            group_files_list = []
            for cf in chunk:
                gf = GroupedFile(
                    filename=cf.filename,
                    relative_path=cf.relative_path,
                    role=cf.role.value,
                    language=cf.language,
                    code_structure=structures.get(cf.filename, structures.get(cf.relative_path)),
                )
                group_files_list.append(gf)

            pg = PackageGroup(
                group_key=key,
                language=dominant_lang,
                file_count=len(chunk),
                tier=2,
                roles=role_counts,
                files=group_files_list,
            )
            result.tier2_groups.append(pg)

    # ─── Tier 3: just counts ───
    for cf in tier3:
        result.tier3_summary[cf.role.value] = result.tier3_summary.get(cf.role.value, 0) + 1
        result.tier3_files.append(cf.relative_path)

    result.total_groups = len(result.tier2_groups)

    logger.info(
        "Grouped %d files: %d tier1 individual, %d tier2 groups, %d tier3 skipped",
        result.total_files,
        len(result.tier1_files),
        result.total_groups,
        len(result.tier3_files),
    )

    return result


def build_group_content(group: PackageGroup) -> str:
    """Build a text summary of a package group for business_context.content.

    This is what D2 will read — structured text, not raw source code.
    """
    lines: list[str] = []
    lines.append(f"Package: {group.group_key} ({group.file_count} files)")
    lines.append(f"Language: {group.language}")
    lines.append(f"Roles: {', '.join(f'{count} {role}' for role, count in group.roles.items())}")
    lines.append("")

    for gf in group.files:
        lines.append(f"--- {gf.filename} ({gf.role}) ---")

        if gf.code_structure:
            cs = gf.code_structure
            if cs.class_name:
                class_line = f"Class: {cs.class_name}"
                if cs.parent_class:
                    class_line += f" extends {cs.parent_class}"
                if cs.interfaces:
                    class_line += f" implements {', '.join(cs.interfaces)}"
                lines.append(class_line)

            if cs.annotations:
                lines.append(f"Annotations: {', '.join(f'@{a}' for a in cs.annotations)}")

            if cs.methods:
                lines.append("Methods:")
                for m in cs.methods[:15]:  # cap at 15 methods per file
                    sig = f"  - {m.name}({m.params})"
                    if m.return_type:
                        sig += f" -> {m.return_type}"
                    if m.annotations:
                        sig += f" [{', '.join(f'@{a}' for a in m.annotations)}]"
                    lines.append(sig)
                if len(cs.methods) > 15:
                    lines.append(f"  ... and {len(cs.methods) - 15} more methods")

            if cs.sql_queries:
                lines.append("SQL queries:")
                for sq in cs.sql_queries[:5]:
                    lines.append(f"  - {sq[:150]}")

            if cs.hardcoded_values:
                lines.append("Hardcoded values:")
                for hv in cs.hardcoded_values[:5]:
                    lines.append(f"  - {hv.name} = {hv.value}")

            if cs.key_comments:
                lines.append("Key comments:")
                for kc in cs.key_comments[:5]:
                    lines.append(f"  - {kc}")

            if cs.dependencies:
                lines.append(f"Dependencies: {', '.join(cs.dependencies[:10])}")

            if cs.entry_points:
                lines.append(f"Entry points: {', '.join(cs.entry_points[:5])}")

        lines.append("")

    return "\n".join(lines)


def build_tier3_summary(summary: dict[str, int], filenames: list[str]) -> str:
    """Build a brief text summary for Tier 3 (skipped) files."""
    lines = [
        f"Tier 3 files (not analyzed individually): {sum(summary.values())} files",
        "",
        "Role breakdown:",
    ]
    for role, count in sorted(summary.items(), key=lambda x: -x[1]):
        lines.append(f"  - {role}: {count} files")

    if filenames:
        lines.append("")
        lines.append("Sample files:")
        for fn in filenames[:20]:
            lines.append(f"  - {fn}")
        if len(filenames) > 20:
            lines.append(f"  ... and {len(filenames) - 20} more")

    return "\n".join(lines)
