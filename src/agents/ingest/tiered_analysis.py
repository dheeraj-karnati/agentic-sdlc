"""Tiered LLM analysis for D1: Ingest.

Replaces the single-prompt approach with three tiers:
- Tier 1: Individual LLM call per high-value file (docs, services, config)
- Tier 2: One LLM call per package group (structured summaries)
- Tier 3: No LLM — count only

Plus a final project-level synthesis call.

Budget: ~50-70 LLM calls for a 2000-file project, ~$0.10 total.
"""

import logging

from src.tools.llm import count_tokens, llm_complete_json

logger = logging.getLogger(__name__)

# Max input tokens per LLM call — leave headroom for prompt template
MAX_INPUT_TOKENS = 7000


def _truncate_to_tokens(text: str, max_tokens: int = MAX_INPUT_TOKENS) -> str:
    """Truncate text to fit within token budget."""
    tokens = count_tokens(text)
    if tokens <= max_tokens:
        return text
    # Rough: 1 token ≈ 4 chars
    char_budget = max_tokens * 4
    half = char_budget // 2
    return text[:half] + "\n\n... [truncated for token budget] ...\n\n" + text[-half:]


# ─── Tier 1: Individual file analysis ───


async def analyze_tier1_file(
    filename: str,
    content: str,
    role: str,
    language: str,
    code_structure: dict | None = None,
    element_summary: dict | None = None,
    provider: str | None = None,
) -> dict:
    """Analyze a single high-value file with LLM.

    For documentation: full content analysis for requirements, domain, project type.
    For code: code structure + source preview for business logic and issues.
    For config: tech stack detection and dependency analysis.

    Returns dict with: document_type, key_topics, importance, summary, business_signals.
    """
    from src.config import settings
    provider = provider or settings.ingest_llm_provider or None

    # Build context based on role
    if role == "documentation":
        content_preview = _truncate_to_tokens(content, 5000)
        structure_info = ""
        if element_summary:
            structure_info = f"\nDocument structure: {element_summary}"
        prompt_context = f"File: {filename} (type: {language}){structure_info}\n\nFull content:\n{content_preview}"
        analysis_focus = (
            "Focus on: requirements, business objectives, stakeholder decisions, "
            "constraints, timelines, compliance needs. Extract the domain and project type."
        )
    elif role == "config":
        content_preview = _truncate_to_tokens(content, 4000)
        prompt_context = f"Configuration file: {filename} (type: {language})\n\nContent:\n{content_preview}"
        analysis_focus = (
            "Focus on: technology stack, frameworks, database connections, "
            "external integrations, security settings, deployment configuration."
        )
    else:
        # Code files — send structure + limited source
        parts = [f"Source file: {filename} (language: {language}, role: {role})"]
        if code_structure:
            cs = code_structure
            if cs.get("class_name"):
                class_line = f"Class: {cs['class_name']}"
                if cs.get("parent_class"):
                    class_line += f" extends {cs['parent_class']}"
                if cs.get("interfaces"):
                    class_line += f" implements {', '.join(cs['interfaces'])}"
                parts.append(class_line)
            if cs.get("annotations"):
                parts.append(f"Annotations: {', '.join(f'@{a}' for a in cs['annotations'])}")
            if cs.get("methods"):
                parts.append("Methods:")
                for m in cs["methods"][:20]:
                    sig = f"  - {m['name']}({m.get('params', '')})"
                    if m.get("return_type"):
                        sig += f" -> {m['return_type']}"
                    parts.append(sig)
            if cs.get("sql_queries"):
                parts.append("Embedded SQL:")
                for sq in cs["sql_queries"][:5]:
                    parts.append(f"  - {sq[:150]}")
            if cs.get("hardcoded_values"):
                parts.append("Hardcoded values:")
                for hv in cs["hardcoded_values"][:5]:
                    parts.append(f"  - {hv.get('name', '?')} = {hv.get('value', '?')}")
            if cs.get("dependencies"):
                parts.append(f"Dependencies: {', '.join(cs['dependencies'][:10])}")
            if cs.get("entry_points"):
                parts.append(f"Entry points: {', '.join(cs['entry_points'][:5])}")
            if cs.get("key_comments"):
                parts.append("Key comments:")
                for kc in cs["key_comments"][:5]:
                    parts.append(f"  - {kc}")

        # Add source preview (truncated)
        source_preview = _truncate_to_tokens(content, 3000)
        parts.append(f"\nSource preview:\n{source_preview}")
        prompt_context = "\n".join(parts)
        analysis_focus = (
            "Focus on: business logic implemented, data validation rules, "
            "integration points, potential bugs or security issues, "
            "hardcoded business thresholds."
        )

    result = await llm_complete_json(
        system=(
            "You are a senior technical analyst for D8X. "
            "Analyze this file and provide a structured assessment. "
            "Be specific — cite exact values, thresholds, and patterns."
        ),
        prompt=f"""{prompt_context}

{analysis_focus}

Respond with this JSON:
{{
    "document_type": "brd|technical_spec|meeting_notes|source_code|database_schema|compliance_doc|process_doc|api_doc|config|build_file|other",
    "key_topics": ["topic1", "topic2", "topic3"],
    "estimated_importance": "critical|high|medium|low",
    "summary": "2-3 sentence summary of what this file contains and why it matters",
    "business_signals": ["specific business rule or pattern found", "another signal"]
}}""",
        provider=provider,
    )

    result["filename"] = filename
    return result


# ─── Tier 2: Group analysis ───


async def analyze_tier2_group(
    group_key: str,
    group_content: str,
    file_count: int,
    roles: dict[str, int],
    language: str,
    provider: str | None = None,
) -> dict:
    """Analyze a package group with LLM using structured summaries.

    Input is the build_group_content() output from package_grouping_skill.
    Much cheaper than per-file analysis since content is pre-structured.

    Returns dict with: group_purpose, key_patterns, data_entities, potential_issues.
    """
    from src.config import settings
    provider = provider or settings.ingest_llm_provider or None

    content_preview = _truncate_to_tokens(group_content, 5000)
    roles_str = ", ".join(f"{count} {role}" for role, count in roles.items())

    result = await llm_complete_json(
        system=(
            "You are a senior solutions architect analyzing a code package. "
            "Summarize the business purpose and key patterns."
        ),
        prompt=f"""Analyze this code package group:

Package: {group_key}
Language: {language}
Files: {file_count} ({roles_str})

Structured content:
{content_preview}

Respond with this JSON:
{{
    "group_purpose": "1-2 sentence description of what this package does in business terms",
    "key_patterns": ["pattern 1 (e.g., CRUD for patients)", "pattern 2"],
    "data_entities": ["entity names this package works with"],
    "potential_issues": ["any concerns found (hardcoded values, missing validation, etc.)"],
    "technology_notes": "frameworks, libraries, or patterns used"
}}""",
        provider=provider,
    )

    result["group_key"] = group_key
    result["file_count"] = file_count
    return result


# ─── Project-level synthesis ───


async def analyze_project_overall(
    tier1_results: list[dict],
    tier2_results: list[dict],
    tier3_summary: dict[str, int],
    total_files: int,
    provider: str | None = None,
) -> dict:
    """Final project-level synthesis after individual analyses.

    Combines all tier results into a single project assessment.
    Backward compatible with the old llm_analysis output format.
    """
    from src.config import settings
    provider = provider or settings.ingest_llm_provider or None

    # Build synthesis input from individual results
    doc_summaries = []
    code_summaries = []
    all_topics: list[str] = []

    for r in tier1_results:
        if isinstance(r, dict):
            summary = f"- {r.get('filename', '?')}: {r.get('summary', '?')}"
            topics = r.get("key_topics", [])
            all_topics.extend(topics)
            if r.get("document_type") in ("brd", "technical_spec", "meeting_notes", "compliance_doc", "process_doc"):
                doc_summaries.append(summary)
            else:
                code_summaries.append(summary)

    for r in tier2_results:
        if isinstance(r, dict):
            code_summaries.append(
                f"- Package {r.get('group_key', '?')} ({r.get('file_count', 0)} files): {r.get('group_purpose', '?')}"
            )

    t3_line = ""
    if tier3_summary:
        t3_parts = [f"{count} {role}" for role, count in tier3_summary.items()]
        t3_line = f"\nTier 3 (not analyzed): {', '.join(t3_parts)}"

    synthesis_input = _truncate_to_tokens(
        f"""PROJECT ANALYSIS SYNTHESIS

Total files: {total_files}
Analyzed individually: {len(tier1_results)} files
Analyzed as groups: {len(tier2_results)} groups{t3_line}

DOCUMENT SUMMARIES:
{chr(10).join(doc_summaries[:20]) or 'No documentation files found.'}

CODE SUMMARIES:
{chr(10).join(code_summaries[:30]) or 'No code files found.'}

KEY TOPICS ACROSS ALL FILES:
{', '.join(list(set(all_topics))[:30]) or 'None identified.'}""",
        6000,
    )

    result = await llm_complete_json(
        system=(
            "You are a senior solutions architect synthesizing analysis results. "
            "Determine the overall project type, domain, and readiness for discovery."
        ),
        prompt=f"""{synthesis_input}

Based on the above analysis, provide a project-level assessment.

Respond with this JSON:
{{
    "project_type": "legacy_modernization" or "greenfield",
    "project_type_reasoning": "brief explanation",
    "domain": "detected industry domain (healthcare, fintech, ecommerce, manufacturing, etc.)",
    "technology_stack": ["tech1", "tech2", "tech3"],
    "overall_assessment": {{
        "strengths": ["what's well covered in the uploaded files"],
        "gaps": ["what's missing that would help analysis"],
        "suggestions": ["specific files or info to add"],
        "ready_for_discovery": true
    }}
}}""",
        provider=provider,
    )

    # Build backward-compatible file_assessments from tier1 results
    result["file_assessments"] = [
        {
            "filename": r.get("filename", ""),
            "document_type": r.get("document_type", "other"),
            "key_topics": r.get("key_topics", []),
            "estimated_importance": r.get("estimated_importance", "medium"),
            "summary": r.get("summary", ""),
        }
        for r in tier1_results
        if isinstance(r, dict) and r.get("filename")
    ]

    return result
