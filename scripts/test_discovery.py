"""
End-to-end test of the Discovery Agent.

1. Creates a project via the FastAPI API
2. Runs the Discovery Agent with sample legacy app text
3. Prints extracted business rules and requirements
4. Shows any clarification questions
5. Stores everything in the business_context table
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# ─── Config ───

API_BASE = "http://127.0.0.1:8000"
SAMPLE_FILE = Path(__file__).parent.parent / "docs" / "sample-legacy-app.txt"


def _header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _print_items(items: list[dict], indent: str = "  ") -> None:
    for i, item in enumerate(items, 1):
        title = item.get("title", "Untitled")
        desc = item.get("description", "")
        extras = {k: v for k, v in item.items() if k not in ("title", "description")}
        extra_str = f"  [{extras}]" if extras else ""
        print(f"{indent}{i}. {title}")
        print(f"{indent}   {desc}{extra_str}")


async def main() -> None:
    document_text = SAMPLE_FILE.read_text()
    print(f"Loaded sample document: {len(document_text)} chars")

    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        # ─── Step 1: Create project ───
        _header("STEP 1: Create Project")
        resp = await client.post("/api/projects/", json={
            "name": "ACME IMS Modernization",
            "description": "Legacy inventory management system analysis",
        })
        if resp.status_code != 201:
            print(f"FAILED to create project: {resp.status_code} {resp.text}")
            sys.exit(1)

        project = resp.json()
        project_id = project["id"]
        print(f"Project created: {project['name']} (id: {project_id})")

    # ─── Step 2: Run Discovery Agent directly ───
    _header("STEP 2: Run Discovery Agent")
    print("Running agent (this calls Claude to analyze the document)...")

    from src.agents.discover.agent import build_discover_graph, create_initial_state
    from src.context_store.database import async_session_factory
    from src.context_store.repository import BusinessContextRepository
    from src.tools.embeddings import embed_text

    async with async_session_factory() as session:
        repo = BusinessContextRepository(session)

        initial_state = create_initial_state(
            project_id=project_id,
            document_text=document_text,
            repository=repo,
            embed_fn=embed_text,
        )

        graph = build_discover_graph()
        compiled = graph.compile()
        final_state = await compiled.ainvoke(initial_state)

        # Commit context entries stored by the agent
        await session.commit()

    # ─── Step 3: Print extracted findings ───
    findings = final_state.get("findings", {})

    _header("STEP 3: Extracted Business Rules")
    rules = findings.get("business_rules", [])
    if rules:
        _print_items(rules)
    else:
        print("  (none extracted)")

    _header("STEP 3: Extracted Requirements")
    reqs = findings.get("requirements", [])
    if reqs:
        _print_items(reqs)
    else:
        print("  (none extracted)")

    _header("STEP 3: Extracted Technical Details")
    tech = findings.get("technical_details", [])
    if tech:
        _print_items(tech)
    else:
        print("  (none extracted)")

    # ─── Step 4: Show clarification questions ───
    _header("STEP 4: Clarification Questions")
    questions = final_state.get("questions", [])
    is_clear = final_state.get("is_clear", True)

    if questions and not is_clear:
        print(f"  Agent has {len(questions)} question(s):\n")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. [{q.get('finding_title', '?')}]")
            print(f"     Q: {q.get('question', '?')}")
            print(f"     Reason: {q.get('reason', '?')}")
            print()
    else:
        print("  All findings are clear — no questions needed.")

    # ─── Step 5: Store findings ───
    _header("STEP 5: Stored Context Entries")

    # If the graph exited early due to questions, we still want to store
    # what was extracted so far. Call store_findings explicitly.
    stored_count = final_state.get("stored_count", 0)
    if stored_count == 0 and findings:
        print("  Graph exited before store_findings (questions pending).")
        print("  Storing extracted findings now...")
        from src.agents.discover.agent import store_findings

        async with async_session_factory() as session:
            repo = BusinessContextRepository(session)
            # Rebuild state with the repo so store_findings can persist
            store_state = dict(final_state)
            store_state["_repository"] = repo
            store_state["_embed_fn"] = embed_text
            result = await store_findings(store_state)
            stored_count = result.get("stored_count", 0)
            await session.commit()

    print(f"  Entries stored in business_context table: {stored_count}")

    # Query the database to verify
    import uuid
    async with async_session_factory() as session:
        repo = BusinessContextRepository(session)
        entries = await repo.get_all_for_project(uuid.UUID(project_id))
        print(f"  Entries found in database: {len(entries)}")
        if entries:
            print()
            categories = {}
            for e in entries:
                categories.setdefault(e.category, []).append(e)
            for cat, items in sorted(categories.items()):
                print(f"  [{cat}] — {len(items)} entries")
                for item in items:
                    has_embedding = item.embedding is not None
                    print(f"    - {item.title} (embedding: {'yes' if has_embedding else 'no'})")

    # ─── Summary ───
    _header("SUMMARY")
    errors = final_state.get("errors", [])
    total_findings = len(rules) + len(reqs) + len(tech)
    print(f"  Business rules:    {len(rules)}")
    print(f"  Requirements:      {len(reqs)}")
    print(f"  Technical details: {len(tech)}")
    print(f"  Total findings:    {total_findings}")
    print(f"  Stored to DB:      {stored_count}")
    print(f"  Questions:         {len(questions)}")
    print(f"  Errors:            {len(errors)}")
    if errors:
        for e in errors:
            print(f"    - {e}")
    print()


if __name__ == "__main__":
    asyncio.run(main())