"""LLM-powered business rule extraction for the Discover agent.

Strategy:
1. Send each document to LLM for individual extraction
2. Merge all extractions
3. Send merged results for cross-source conflict detection
4. Generate clarification questions
5. Build system understanding
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.context_store.models import BusinessContext
from src.tools.llm import llm_complete_json

logger = logging.getLogger(__name__)


async def discover_business_rules(
    project_id: uuid.UUID,
    ingested_content: list[dict],
    db: AsyncSession,
    provider: str | None = None,
) -> dict:
    """Use LLM to extract business rules, entities, conflicts, and questions.

    Args:
        project_id: The project UUID.
        ingested_content: List of dicts with 'filename' and 'content' keys.
        db: Async database session.
        provider: LLM provider override.

    Returns:
        Dict with business_rules, domain_entities, conflicts,
        clarification_questions, system_understanding, metrics, quality_assessment.
    """
    from src.config import settings
    provider = provider or settings.discover_llm_provider or None

    # Get ingested source content from business_context table
    result = await db.execute(
        select(BusinessContext).where(
            BusinessContext.project_id == project_id,
            BusinessContext.category == "ingested_source",
        )
    )
    sources_from_db = list(result.scalars().all())

    # Build source texts — prefer DB, fall back to passed-in content
    if sources_from_db:
        source_texts = [
            {"filename": s.title or "unknown", "content": s.content or ""}
            for s in sources_from_db
        ]
    elif ingested_content:
        source_texts = [
            {
                "filename": item.get("source_file", item.get("filename", "unknown")),
                "content": item.get("content", item.get("title", "")),
            }
            for item in ingested_content
        ]
    else:
        logger.warning("No source content found for project %s", project_id)
        source_texts = []

    all_rules: list[dict] = []
    all_entities: list[dict] = []
    all_defects: list[dict] = []
    rule_counter = 1
    entity_names_seen: set[str] = set()

    # === Phase 1: Extract from each source individually ===
    for source in source_texts:
        content_preview = source["content"][:6000]
        if not content_preview.strip():
            continue

        try:
            extraction = await llm_complete_json(
                system=(
                    "You are a senior business analyst and security auditor. "
                    "Extract business rules, domain entities, AND identify "
                    "defects, bugs, and security vulnerabilities in the source. "
                    "Be thorough and specific — cite exact function names, "
                    "line references, variable names, and hardcoded values."
                ),
                prompt=f"""Analyze this document and extract business rules, domain entities, AND any defects or vulnerabilities.

SOURCE FILE: {source['filename']}

CONTENT:
{content_preview}

Respond with this JSON:
{{
    "business_rules": [
        {{
            "name": "short descriptive name",
            "description": "detailed description including specific values, thresholds, function names, and conditions",
            "category": "one of: authentication, authorization, data_validation, workflow, integration, compliance, business_logic, scheduling, billing, clinical, reporting, security",
            "confidence": "high|medium|low"
        }}
    ],
    "entities": [
        {{
            "name": "EntityName",
            "type": "core_entity|actor|transaction|document|reference|junction|system",
            "attributes": ["attr1", "attr2", "attr3"],
            "relationships": ["relationship description 1"]
        }}
    ],
    "defects": [
        {{
            "name": "short descriptive name",
            "description": "detailed description of the bug, vulnerability, or defect with exact code references",
            "category": "sql_injection|xss|data_exposure|logic_bug|race_condition|hardcoded_secret|deprecated_code|missing_validation|compliance_violation|performance|other",
            "severity": "critical|high|medium|low",
            "location": "exact function name, stored procedure, or section where the defect exists"
        }}
    ]
}}

IMPORTANT — for source code and database files, look carefully for:
- SQL injection (string concatenation in queries, unsanitized inputs)
- Sensitive data stored in plaintext (SSN, passwords, credit cards)
- Hardcoded secrets, API keys, or credentials
- Missing input validation or sanitization
- Logic bugs (off-by-one, wrong comparisons, missing null checks)
- Race conditions or concurrency issues
- Deprecated codes, standards, or APIs still in use
- Missing error handling or silent failures
- Time/date handling bugs (timezone issues, duration vs point-in-time)

For BRDs and requirements docs, look for:
- Contradictions within the same document
- Ambiguous or untestable requirements
- Missing edge cases or error scenarios
- Unrealistic performance targets""",
                provider=provider,
            )

            for rule in extraction.get("business_rules", []):
                rule["id"] = f"BR-{rule_counter:03d}"
                rule["source"] = source["filename"]
                all_rules.append(rule)
                rule_counter += 1

            for entity in extraction.get("entities", []):
                if entity["name"] not in entity_names_seen:
                    entity_names_seen.add(entity["name"])
                    all_entities.append(entity)

            # Collect defects found in this source
            for defect in extraction.get("defects", []):
                defect["source"] = source["filename"]
                all_defects.append(defect)

        except Exception as e:
            logger.warning("Extraction failed for %s: %s", source["filename"], e)
            continue

    # === Phase 2: Conflict, defect & vulnerability detection ===
    conflicts: list[dict] = []

    if all_rules or all_defects:
        rules_summary = "\n".join(
            f"- {r['id']} ({r['source']}): {r['name']} — {r['description'][:200]}"
            for r in all_rules[:120]
        )
        defects_summary = "\n".join(
            f"- [{d['severity']}] {d['name']} in {d.get('location','unknown')} ({d['source']}): {d['description'][:200]}"
            for d in all_defects
        ) or "No defects detected in Phase 1."
        sources_list = ", ".join(s["filename"] for s in source_texts)

        try:
            conflict_result = await llm_complete_json(
                system=(
                    "You are a senior security auditor, QA lead, and business analyst "
                    "performing a comprehensive cross-source analysis. You find conflicts "
                    "between documents, security vulnerabilities in code, compliance violations, "
                    "logic bugs, and gaps between requirements and implementation. "
                    "Be SPECIFIC — cite exact function names, variable names, line references, "
                    "threshold values, and code patterns. Never be vague."
                ),
                prompt=f"""Perform a comprehensive conflict, defect, and vulnerability analysis across these sources.

SOURCES ANALYZED: {sources_list}

DEFECTS ALREADY FOUND IN CODE/SCHEMA:
{defects_summary}

KEY BUSINESS RULES ({len(all_rules)} total):
{rules_summary}

FULL SOURCE CONTENT:
{chr(10).join(f"=== {s['filename']} ==={chr(10)}{s['content'][:5000]}" for s in source_texts[:8])}

Find ALL of the following — aim for 10-20 findings:

**CROSS-SOURCE CONFLICTS** (values differ between documents):
- Thresholds, limits, or numeric values that differ between BRD and code
- Business rules stated in requirements but implemented differently in code
- Data formats or validation rules that don't match between schema and BRD

**SECURITY VULNERABILITIES** (in code or schema):
- SQL injection (string concatenation in queries, f-strings in SQL, unsanitized user input)
- Sensitive data exposure (SSN, passwords, credit cards stored in plaintext without encryption)
- Hardcoded secrets, API keys, or credentials in source code
- Missing authentication or authorization checks
- Insecure session management or token handling

**COMPLIANCE VIOLATIONS** (code vs stated compliance requirements):
- HIPAA/PCI/SOX requirements stated in BRD but not enforced in code
- Audit logging requirements not implemented
- Data retention or encryption requirements not met

**LOGIC BUGS & DEFECTS** (in source code):
- Scheduling/time bugs (checking time without duration, timezone issues)
- Duplicate detection mismatches (different algorithms in different places)
- Off-by-one errors, wrong comparisons, missing edge cases
- Deprecated codes, standards, or APIs still in use (e.g., removed CPT codes, outdated ICD versions)
- Missing null checks or error handling

**IMPLEMENTATION GAPS** (requirements without code):
- Features described in BRD with no corresponding code
- Database tables referenced in requirements but missing from schema

Respond with this JSON:
{{
    "conflicts": [
        {{
            "type": "security_vulnerability|data_conflict|implementation_gap|compliance_violation|logic_bug|deprecated_code|data_exposure|ambiguity",
            "description": "DETAILED description with exact function names, variable names, specific values, and code references",
            "severity": "critical|high|medium|low",
            "source_a": "filename where one version/issue is found",
            "source_b": "filename where conflicting version is found (or same file for single-source issues)",
            "location": "exact function, procedure, or section name",
            "resolution_options": ["specific fix option 1", "specific fix option 2"]
        }}
    ]
}}

IMPORTANT: Do NOT return an empty list. Every real codebase has security issues and conflicts.
If you found defects in Phase 1, include them as conflicts here with full details.""",
                provider=provider,
            )

            conflicts = conflict_result.get("conflicts", [])
            for i, c in enumerate(conflicts):
                c["id"] = f"CON-{i + 1:03d}"

        except Exception as e:
            logger.warning("Conflict detection failed: %s", e)

        # If LLM conflict detection failed but we have Phase 1 defects, convert them
        if not conflicts and all_defects:
            for i, d in enumerate(all_defects):
                conflicts.append({
                    "id": f"CON-{i + 1:03d}",
                    "type": "security_vulnerability" if d["category"] in ("sql_injection", "xss", "data_exposure", "hardcoded_secret") else "logic_bug",
                    "description": f"{d['name']}: {d['description']}",
                    "severity": d.get("severity", "medium"),
                    "source_a": d.get("source", "unknown"),
                    "source_b": d.get("source", "unknown"),
                    "location": d.get("location", ""),
                    "resolution_options": [],
                })

    # === Phase 3: Generate clarification questions ===
    questions: list[dict] = []

    if all_rules:
        try:
            conflicts_summary = "\n".join(
                f"- {c['id']} ({c['severity']}): {c['description'][:150]}"
                for c in conflicts
            ) or "No conflicts detected."

            low_confidence = [r for r in all_rules if r.get("confidence") != "high"][:20]
            low_conf_summary = "\n".join(
                f"- {r['id']}: {r['name']} (confidence: {r['confidence']})"
                for r in low_confidence
            ) or "All rules have high confidence."

            questions_result = await llm_complete_json(
                system=(
                    "You are a senior business analyst preparing "
                    "questions for stakeholders. Generate specific, "
                    "actionable questions that will resolve ambiguities "
                    "and conflicts found during analysis."
                ),
                prompt=f"""Based on analyzing {len(source_texts)} source files, {len(all_rules)} business rules, and {len(conflicts)} conflicts detected, generate clarification questions.

KEY CONFLICTS:
{conflicts_summary}

RULES WITH MEDIUM/LOW CONFIDENCE:
{low_conf_summary}

Generate 5-10 questions that:
1. Resolve blocking conflicts (highest priority)
2. Clarify ambiguous requirements
3. Fill gaps in documentation
4. Confirm assumptions

Respond with this JSON:
{{
    "questions": [
        {{
            "question": "specific question text",
            "impact": "what design decisions are blocked without this answer",
            "priority": "blocking|high|medium|low",
            "related_conflict": "CON-XXX or null"
        }}
    ]
}}""",
                provider=provider,
            )

            questions = questions_result.get("questions", [])
            for i, q in enumerate(questions):
                q["id"] = f"Q-{i + 1:03d}"

        except Exception as e:
            logger.warning("Question generation failed: %s", e)

    # === Phase 4: System understanding ===
    system_understanding: dict = {}

    if all_rules or all_entities:
        try:
            system_understanding = await llm_complete_json(
                system="You are a senior solutions architect building a comprehensive understanding of a software system.",
                prompt=f"""Based on analyzing {len(source_texts)} documents, {len(all_rules)} business rules, and {len(all_entities)} entities, generate a system understanding.

KEY ENTITIES: {', '.join(e['name'] for e in all_entities[:20])}

TOP RULES: {chr(10).join(f"- {r['name']}: {r['description'][:100]}" for r in all_rules[:15])}

SOURCE FILES: {', '.join(s['filename'] for s in source_texts)}

Respond with this JSON:
{{
    "purpose": "2-3 sentence description of what this system does",
    "domain": "industry domain (healthcare, fintech, ecommerce, etc.)",
    "current_state": "description of current system state or 'New system' if greenfield",
    "key_workflows": ["workflow 1 description", "workflow 2", "workflow 3"],
    "critical_risks": ["risk 1", "risk 2", "risk 3"],
    "modernization_scope": "brief description of what needs to be built/modernized"
}}""",
                provider=provider,
            )

        except Exception as e:
            logger.warning("System understanding failed: %s", e)

    # === Phase 5: Quality assessment ===
    total_rules = len(all_rules)
    total_entities = len(all_entities)
    total_conflicts = len(conflicts)
    total_defects = len(all_defects)

    completeness = min(100, total_rules * 2 + total_entities * 3)
    depth = min(100, sum(1 for r in all_rules if r.get("confidence") == "high") * 5)
    consistency = max(0, 100 - total_conflicts * 3)
    traceability = min(100, sum(1 for r in all_rules if r.get("source")) * 3)
    actionability = min(100, 50 + total_rules + total_entities)
    # Security score penalized by critical/high defects
    critical_defects = sum(1 for d in all_defects if d.get("severity") in ("critical", "high"))
    security = max(0, 100 - critical_defects * 15)

    quality_score = int(
        completeness * 0.20
        + depth * 0.20
        + consistency * 0.15
        + traceability * 0.10
        + actionability * 0.10
        + security * 0.25
    )

    return {
        "business_rules": all_rules,
        "domain_entities": all_entities,
        "conflicts": conflicts,
        "defects": all_defects,
        "clarification_questions": questions,
        "system_understanding": system_understanding,
        "metrics": {
            "rules_found": total_rules,
            "entities": total_entities,
            "conflicts": total_conflicts,
            "defects": total_defects,
            "quality_score": quality_score,
        },
        "quality_assessment": {
            "score": quality_score,
            "completeness": completeness,
            "depth": depth,
            "consistency": consistency,
            "traceability": traceability,
            "actionability": actionability,
            "security": security,
        },
    }
