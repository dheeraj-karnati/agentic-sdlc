"""Integration test: run the full Discovery Agent workflow against sample legacy app.

Uses Ollama (local LLM) exclusively — no API costs.
Prints detailed results including business rules, conflicts, quality scores, etc.

Usage:
    uv run python scripts/run_discovery_integration.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_legacy_app"


def load_fixtures() -> list[dict[str, str]]:
    """Load all fixture files."""
    files = []
    for filename in ("source_code.py", "brd.md", "meeting_notes.md", "schema.sql"):
        filepath = FIXTURE_DIR / filename
        files.append({
            "filename": filename,
            "content": filepath.read_text(),
        })
    return files


def print_separator(title: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}\n")


def print_subsection(title: str) -> None:
    print(f"\n  ── {title} {'─' * max(1, 50 - len(title))}\n")


async def main() -> None:
    start_time = time.time()

    # Use cloud providers — Claude API for LLM, OpenAI for embeddings
    # Load keys from .env.local (has API keys that .env does not)
    from dotenv import load_dotenv

    env_local = Path(__file__).parent.parent / ".env.local"
    if env_local.exists():
        load_dotenv(env_local, override=True)

    # Re-create settings so it picks up the .env.local values
    import src.config
    from src.config import Settings

    src.config.settings = Settings()
    settings = src.config.settings

    from src.agents.discover.agent import DiscoverWorkflow, create_initial_state

    # Detect provider
    if settings.anthropic_api_key:
        provider = "Claude API (claude-sonnet-4)"
    elif settings.ollama_model:
        provider = f"Ollama ({settings.ollama_model})"
    else:
        print("ERROR: No ANTHROPIC_API_KEY in .env and no Ollama configured.")
        return

    embed_provider = "OpenAI (text-embedding-3-small)" if settings.openai_api_key else "Mock (1536-dim)"

    print_separator("DISCOVERY AGENT INTEGRATION TEST")
    print(f"  LLM:    {provider}")
    print(f"  Embed:  {embed_provider}")
    print("  Input:  4 files (source_code.py, brd.md, meeting_notes.md, schema.sql)")

    # Load fixture files
    files = load_fixtures()
    total_chars = sum(len(f["content"]) for f in files)
    print(f"  Total input size: {total_chars:,} characters across {len(files)} files")

    # Get LLM from centralized factory (reads .env automatically)
    from src.tools.llm import get_llm

    llm = get_llm(max_tokens=8192)

    # Build initial state — no database, use mock repo to capture stores
    stored_items: list[dict] = []
    mock_repo = AsyncMock()

    async def capture_store(**kwargs):
        stored_items.append(kwargs)

    mock_repo.store_context = AsyncMock(side_effect=capture_store)

    # Use real embeddings if OpenAI key available, else mock
    embed_calls: list[str] = []

    if settings.openai_api_key:
        from src.tools.embeddings import embed_text

        async def tracked_embed(text: str) -> list[float]:
            embed_calls.append(text[:80])
            return await embed_text(text)

        embed_fn = tracked_embed
    else:
        async def mock_embed(text: str) -> list[float]:
            embed_calls.append(text[:80])
            return [0.01 * (hash(text) % 100)] * 1536

        embed_fn = mock_embed

    initial_state = create_initial_state(
        project_id="00000000-0000-0000-0000-000000000001",
        files=files,
        llm=llm,
        repository=mock_repo,
        embed_fn=embed_fn,
    )

    # Compile and run the workflow
    print_separator("RUNNING WORKFLOW")

    workflow = DiscoverWorkflow()
    compiled = workflow.compile()

    try:
        result = await compiled.ainvoke(initial_state)
    except Exception as e:
        print(f"\n  ❌ WORKFLOW FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    elapsed = time.time() - start_time

    # ─── Extract results ───
    task_outputs = result.get("task_outputs", {})
    errors = result.get("errors", [])

    # Classification results
    classified = task_outputs.get("parse_and_classify", {})
    classified_items = classified.get("items", [])

    # Deep analysis results
    deep = task_outputs.get("deep_analysis", {})
    business_rules = deep.get("business_rules", [])
    entities = deep.get("entities", [])
    conflict_report = deep.get("conflict_report", {})
    code_analyses = deep.get("code_analyses", [])
    doc_extractions = deep.get("document_extractions", [])
    schema_analyses = deep.get("schema_analyses", [])

    # System understanding
    understanding = task_outputs.get("system_understanding", {})

    # Clarification questions
    questions_data = task_outputs.get("clarification_questions", {})
    questions = questions_data.get("questions", [])

    # Quality assessment
    quality = task_outputs.get("quality_assessment", {})
    scores = quality.get("scores", {})
    overall_score = quality.get("overall_score", result.get("quality_score", 0))
    suggestions = quality.get("suggestions", result.get("quality_suggestions", []))

    # ─── Print Results ───

    print_separator("1. INPUT CLASSIFICATION")
    for item in classified_items:
        print(f"  [{item.get('content_type', '?'):15s}]  {item.get('source', '?'):25s}  "
              f"lang={item.get('language', '-')}")
    if not classified_items:
        print("  (no items classified — check errors)")

    print_separator("2. BUSINESS RULES EXTRACTED")
    print(f"  Total rules: {len(business_rules)}")
    for i, rule in enumerate(business_rules, 1):
        print(f"\n  Rule {i}: {rule.get('rule_name', rule.get('rule_id', 'N/A'))}")
        print(f"    Confidence:  {rule.get('confidence', 'N/A')}")
        print(f"    Trigger:     {rule.get('trigger_condition', 'N/A')[:100]}")
        print(f"    Action:      {rule.get('action', 'N/A')[:100]}")
        if rule.get('exceptions'):
            print(f"    Exceptions:  {rule['exceptions']}")
        print(f"    Source:      {rule.get('source_reference', 'N/A')[:80]}")

    print_separator("3. DOMAIN ENTITIES EXTRACTED")
    print(f"  Total entities: {len(entities)}")
    for entity in entities:
        attrs = entity.get("attributes", [])
        rels = entity.get("relationships", [])
        print(f"\n  {entity.get('entity_name', '?')} ({entity.get('entity_type', '?')})")
        print(f"    {entity.get('description', '')[:100]}")
        if attrs:
            attr_names = [a.get("name", "?") for a in attrs[:5]]
            print(f"    Attributes: {', '.join(attr_names)}")
        if rels:
            for r in rels[:3]:
                print(f"    → {r.get('relationship_type', '?')} {r.get('related_entity', '?')} ({r.get('cardinality', '?')})")

    print_separator("4. CONFLICTS DETECTED")
    contradictions = conflict_report.get("contradictions", [])
    gaps = conflict_report.get("gaps", [])
    ambiguities = conflict_report.get("ambiguities", [])
    redundancies = conflict_report.get("redundancies", [])
    total_conflicts = len(contradictions) + len(gaps) + len(ambiguities) + len(redundancies)

    print(f"  Total: {total_conflicts} conflicts")
    print(f"    Contradictions: {len(contradictions)}")
    print(f"    Gaps:           {len(gaps)}")
    print(f"    Ambiguities:    {len(ambiguities)}")
    print(f"    Redundancies:   {len(redundancies)}")

    if contradictions:
        print_subsection("Contradictions")
        for c in contradictions:
            print(f"  ⚡ [{c.get('severity', '?')}] {c.get('description', '?')[:120]}")
            if c.get("suggested_resolution"):
                print(f"     Resolution: {c['suggested_resolution'][:100]}")

    if gaps:
        print_subsection("Gaps")
        for g in gaps:
            print(f"  🔍 [{g.get('severity', '?')}] {g.get('description', '?')[:120]}")

    if ambiguities:
        print_subsection("Ambiguities")
        for a in ambiguities:
            print(f"  ❓ [{a.get('severity', '?')}] {a.get('description', '?')[:120]}")

    print_separator("5. QUALITY ASSESSMENT")
    print(f"  Overall Score: {overall_score:.1f} / 100  "
          f"({'PASS ✓' if overall_score >= 70 else 'FAIL ✗'})")
    print(f"  Quality Retries Used: {result.get('quality_retries', 0)}")
    print()
    for dim in ("completeness", "depth", "consistency", "traceability", "actionability"):
        val = scores.get(dim, 0)
        bar = "█" * int(val / 5) + "░" * (20 - int(val / 5))
        print(f"    {dim:15s}  {bar}  {val:.0f}")

    if suggestions:
        print_subsection("Improvement Suggestions")
        for s in suggestions:
            print(f"  • {s}")

    print_separator("6. CLARIFICATION QUESTIONS")
    print(f"  Total questions: {len(questions)}")
    for i, q in enumerate(questions, 1):
        print(f"\n  Q{i} [{q.get('priority', '?')}]: {q.get('question', '?')}")
        print(f"      Why: {q.get('why_asking', 'N/A')[:100]}")
        print(f"      Impact: {q.get('impact_if_unanswered', 'N/A')[:100]}")
        if q.get("suggested_options"):
            print(f"      Options: {q['suggested_options']}")

    print_separator("7. SYSTEM UNDERSTANDING SUMMARY")
    purpose = understanding.get("system_purpose", "")
    print(f"  System Purpose ({len(purpose)} chars):")
    if purpose:
        print(f"    {purpose[:300]}...")
    else:
        print("    (not generated)")

    workflows = understanding.get("user_workflows", [])
    print(f"\n  User Workflows: {len(workflows)}")
    for wf in workflows[:5]:
        steps = wf.get("steps", [])
        print(f"    • {wf.get('journey_name', '?')} ({wf.get('actor', '?')}) — {len(steps)} steps")

    recs = understanding.get("modernization_recommendations", [])
    print(f"\n  Modernization Recommendations: {len(recs)}")
    for rec in recs[:5]:
        print(f"    • [{rec.get('priority', '?')}] {rec.get('area', '?')}: {rec.get('recommendation', '')[:80]}")

    print_separator("8. STORAGE VERIFICATION")
    print(f"  Items stored to business_context: {result.get('stored_count', 0)}")
    print(f"  Mock store_context calls: {mock_repo.store_context.await_count}")
    print(f"  Embeddings computed: {len(embed_calls)}")

    categories = {}
    for item in stored_items:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    print(f"\n  By category:")
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count}")

    print_separator("9. EXTRACTION COUNTS BY SOURCE")
    print(f"  Code analyses:       {len(code_analyses)}")
    print(f"  Document extractions: {len(doc_extractions)}")
    print(f"  Schema analyses:     {len(schema_analyses)}")

    # Show code analysis details if available
    if code_analyses:
        ca = code_analyses[0]
        mods = ca.get("module_structure", [])
        apis = ca.get("api_surface", [])
        queries = ca.get("database_queries", [])
        tech = ca.get("technology_stack", [])
        patterns = ca.get("code_patterns", [])
        smells = ca.get("code_smells", [])
        print(f"\n  Code analysis (first file):")
        print(f"    API endpoints found:  {len(apis)}")
        print(f"    DB queries found:     {len(queries)}")
        print(f"    Technology detected:   {tech}")
        print(f"    Design patterns:       {patterns}")
        print(f"    Code smells:           {len(smells)}")
        for smell in smells:
            print(f"      ⚠ {smell.get('smell_type', '?')}: {smell.get('description', '')[:80]}")

    if schema_analyses:
        sa = schema_analyses[0]
        tables = sa.get("tables", [])
        rels = sa.get("relationships", [])
        patterns = sa.get("data_patterns", [])
        norm = sa.get("normalization_issues", [])
        missing = sa.get("missing_constraints", [])
        print(f"\n  Schema analysis:")
        print(f"    Tables found:           {len(tables)}")
        print(f"    FK relationships:       {len(rels)}")
        print(f"    Data patterns:          {[p.get('pattern_name') for p in patterns]}")
        print(f"    Normalization issues:   {len(norm)}")
        print(f"    Missing constraints:    {len(missing)}")
        for m in missing[:5]:
            print(f"      ⚠ {m}")

    if errors:
        print_separator("ERRORS")
        for e in errors:
            print(f"  ❌ {e}")

    print_separator("DONE")
    print(f"  Total elapsed time: {elapsed:.1f} seconds")
    print(f"  LLM calls made: ~{8 + result.get('quality_retries', 0) * 7} (estimated)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
