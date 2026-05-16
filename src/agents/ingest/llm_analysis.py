"""LLM-powered analysis of ingested content for the Ingest agent."""

import logging

from src.tools.llm import llm_complete_json

logger = logging.getLogger(__name__)


async def analyze_ingested_content(
    parsed_files: list[dict],
    provider: str | None = None,
) -> dict:
    """Use LLM to analyze parsed file contents after file parsing.

    Returns enriched analysis: project type, domain, file assessments,
    and overall readiness for discovery.
    """
    from src.config import settings
    provider = provider or settings.ingest_llm_provider or None

    # Build summary of all files for the LLM
    file_summaries = []
    for f in parsed_files:
        content_preview = f.get("content", f.get("description", ""))[:3000]
        element_info = ""
        if f.get("element_summary"):
            element_info = f"\nDocument structure: {f['element_summary']}"
        file_summaries.append(
            f"File: {f['filename']} (type: {f.get('file_type', 'unknown')}){element_info}\n"
            f"Content preview:\n{content_preview}\n---"
        )

    all_summaries = "\n\n".join(file_summaries)

    result = await llm_complete_json(
        system=(
            "You are a senior technical analyst for D8X, "
            "an AI-powered SDLC platform. You analyze uploaded "
            "project documents to prepare them for downstream "
            "requirement extraction and system design."
        ),
        prompt=f"""Analyze these {len(parsed_files)} uploaded files and provide a structured assessment.

FILES:
{all_summaries}

Respond with this exact JSON structure:
{{
    "project_type": "legacy_modernization" or "greenfield",
    "project_type_reasoning": "brief explanation",
    "domain": "detected industry domain (healthcare, fintech, ecommerce, etc.)",
    "file_assessments": [
        {{
            "filename": "exact filename",
            "document_type": "brd|technical_spec|meeting_notes|source_code|database_schema|compliance_doc|process_doc|api_doc|user_story|other",
            "key_topics": ["topic1", "topic2", "topic3"],
            "estimated_importance": "critical|high|medium|low",
            "summary": "2-3 sentence summary of what this file contains"
        }}
    ],
    "overall_assessment": {{
        "strengths": ["what's well covered"],
        "gaps": ["what's missing that would help analysis"],
        "suggestions": ["specific files/info to add"],
        "ready_for_discovery": true
    }}
}}""",
        provider=provider,
    )

    return result
