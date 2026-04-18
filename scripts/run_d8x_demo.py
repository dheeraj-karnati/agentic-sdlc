"""D8X End-to-End Demo: D1 Ingest → D2 Discover → D3 Design → D4 Prototype

Two modes:
  REPLAY (default): loads cached outputs for D1-D3, only runs D4 live (free/cheap)
  LIVE:             runs all 4 agents against the LLM (costs ~$0.50-1.00)

Usage:
    # Replay mode (default) — uses cached fixtures, only D4 calls LLM:
    uv run python scripts/run_d8x_demo.py

    # Replay with custom PRD:
    uv run python scripts/run_d8x_demo.py tests/fixtures/greenfield_prd/prd.md

    # Live mode — all agents call the LLM:
    uv run python scripts/run_d8x_demo.py --live tests/fixtures/greenfield_prd/prd.md

    # Skip D4 prototype (just show D1-D3 output):
    uv run python scripts/run_d8x_demo.py --skip-prototype
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "cached_pipeline"


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_step(step: str, desc: str) -> None:
    print(f"\n  {'─' * 50}")
    print(f"  {step}: {desc}")
    print(f"  {'─' * 50}\n")


def print_kv(key: str, value: object) -> None:
    print(f"  {key:.<30s} {value}")


def load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        print(f"  WARNING: Fixture {path} not found")
        return {}
    return json.loads(path.read_text())


async def main() -> None:
    start = time.time()

    # Parse args
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    live_mode = "--live" in sys.argv
    skip_proto = "--skip-prototype" in sys.argv

    # ─── Load API keys (only needed for live mode or D4) ───
    from dotenv import load_dotenv
    env_local = Path(__file__).parent.parent / ".env.local"
    if env_local.exists():
        load_dotenv(env_local, override=True)

    import src.config
    from src.config import Settings
    src.config.settings = Settings()
    settings = src.config.settings

    use_ollama = "--ollama" in sys.argv

    llm = None
    if live_mode or not skip_proto:
        if use_ollama or not settings.anthropic_api_key:
            from langchain_ollama import ChatOllama
            model = "qwen2.5-coder:32b"
            llm = ChatOllama(
                model=model, base_url="http://localhost:11434",
                num_predict=8192, keep_alive="30m", timeout=600, format="json",
            )
            provider = f"Ollama ({model}, local)"
        elif settings.anthropic_api_key:
            from src.tools.llm import get_llm
            llm = get_llm(max_tokens=8192)
            provider = "Claude API"
        else:
            provider = "NONE (no API key)"
    else:
        provider = "NONE (replay mode)"

    mode = "LIVE" if live_mode else "REPLAY (cached D1-D3)"
    print_header("D8X DEMO — Full Pipeline")
    print(f"  Mode: {mode}")
    print(f"  LLM: {provider}")

    # ─── Resolve input files ───
    if not args:
        args = ["tests/fixtures/greenfield_prd/prd.md"]
    print(f"  Input: {', '.join(args)}")

    files: list[dict[str, str]] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            for f in sorted(p.iterdir()):
                if f.is_file() and not f.name.startswith("."):
                    files.append({"filename": f.name, "content": f.read_text(errors="replace")})
        elif p.is_file():
            files.append({"filename": p.name, "content": p.read_text(errors="replace")})

    total_chars = sum(len(f["content"]) for f in files)
    print(f"  Files: {len(files)} ({total_chars:,} characters)")

    # ─── Mock repo ───
    stored_items: list[dict] = []
    mock_repo = AsyncMock()
    async def capture_store(**kwargs: object) -> None:
        stored_items.append(dict(kwargs))
    mock_repo.store_context = AsyncMock(side_effect=capture_store)
    mock_repo.get_all_for_project = AsyncMock(return_value=[])

    async def mock_embed(text: str) -> list[float]:
        return [0.01] * 1536

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    project_id = "00000000-0000-0000-0000-000000000001"

    # ═══════════════════════════════════════════
    # D1: INGEST
    # ═══════════════════════════════════════════
    if live_mode:
        print_step("D1", "INGEST — Parsing input files (LIVE)")
        from src.agents.ingest.agent import IngestWorkflow, create_initial_state as create_ingest_state
        ingest_state = create_ingest_state(
            project_id=project_id, files=files, llm=llm, repository=mock_repo, embed_fn=mock_embed,
        )
        ingest_result = await IngestWorkflow().compile().ainvoke(ingest_state)
        ingest_outputs = ingest_result.get("task_outputs", {})
    else:
        print_step("D1", "INGEST — Loading cached output")
        ingest_result = load_fixture("d1_ingest")
        ingest_outputs = ingest_result.get("task_outputs", {})
        # Inject actual file content into the cached bundle
        bundle = ingest_outputs.get("structured_bundle", {})
        if bundle.get("sources") and files:
            bundle["sources"][0]["text"] = files[0]["content"]

    quality = ingest_outputs.get("quality_report", {})
    inventory = ingest_outputs.get("source_inventory", {})
    print_kv("Sources ingested", inventory.get("total_sources", 0))
    print_kv("Total words", f"{inventory.get('total_words', 0):,}")
    print_kv("Quality", f"{quality.get('overall_score', 0):.0f}/100 {'PASS' if quality.get('passing') else 'REVIEW'}")

    # ═══════════════════════════════════════════
    # D2: DISCOVER
    # ═══════════════════════════════════════════
    if live_mode:
        print_step("D2", "DISCOVER — Extracting rules & entities (LIVE)")
        from src.agents.discover.agent import DiscoverWorkflow, create_initial_state as create_discover_state
        bundle = ingest_outputs.get("structured_bundle", {})
        discover_files = [
            {"filename": s.get("original_filename", "src"), "content": s.get("text", "")}
            for s in bundle.get("sources", []) if s.get("text")
        ]
        discover_state = create_discover_state(
            project_id=project_id, files=discover_files, llm=llm, repository=mock_repo, embed_fn=mock_embed,
        )
        discover_result = await DiscoverWorkflow().compile().ainvoke(discover_state)
        disc_outputs = discover_result.get("task_outputs", {})
    else:
        print_step("D2", "DISCOVER — Loading cached output")
        discover_result = load_fixture("d2_discover")
        disc_outputs = discover_result.get("task_outputs", {})

    deep = disc_outputs.get("deep_analysis", {})
    rules = deep.get("business_rules", [])
    entities = deep.get("entities", [])
    conflicts = deep.get("conflict_report", {})
    print_kv("Business rules", len(rules))
    print_kv("Domain entities", len(entities))
    print_kv("Conflicts/gaps", conflicts.get("total_conflicts", 0))
    print_kv("Quality", f"{disc_outputs.get('quality_assessment', {}).get('overall_score', discover_result.get('quality_score', 0)):.0f}/100")

    # Show top rules
    print("\n  Top business rules:")
    for r in rules[:5]:
        print(f"    {r.get('rule_id', '?'):8s} {r.get('rule_name', '')}")

    # ═══════════════════════════════════════════
    # D3: DESIGN
    # ═══════════════════════════════════════════
    if live_mode:
        print_step("D3", "DESIGN — Architecture + schema + API (LIVE)")
        mock_entries = []
        for item in stored_items:
            entry = MagicMock()
            entry.category = item.get("category", "")
            entry.title = item.get("title", "")
            entry.content = item.get("content", "")
            entry.metadata_ = item.get("metadata", {})
            mock_entries.append(entry)
        mock_repo.get_all_for_project = AsyncMock(return_value=mock_entries)
        from src.agents.design.agent import DesignWorkflow, create_initial_state as create_design_state
        design_state = create_design_state(
            project_id=project_id, llm=llm, repository=mock_repo, session=mock_session,
        )
        design_result = await DesignWorkflow().compile().ainvoke(design_state)
        design_outputs = design_result.get("task_outputs", {})
    else:
        print_step("D3", "DESIGN — Loading cached output")
        design_result = load_fixture("d3_design")
        design_outputs = design_result.get("task_outputs", {})

    arch = design_outputs.get("architecture", {})
    schema = design_outputs.get("database_schema", {})
    api = design_outputs.get("api_specification", {})
    auth = design_outputs.get("auth_design", {})
    frontend = design_outputs.get("frontend_components", {})

    print_kv("Architecture", arch.get("pattern", "N/A"))
    stack = ", ".join(c.get("technology", "") for c in arch.get("recommended_stack", [])[:4])
    print_kv("Tech stack", stack)
    print_kv("DB tables", len(schema.get("tables", [])))
    print_kv("API endpoints", len(api.get("endpoints", [])))
    print_kv("Auth roles", len(auth.get("roles", [])))
    print_kv("Frontend routes", len(frontend.get("routes", [])))
    print_kv("Quality", f"{design_outputs.get('quality_assessment', {}).get('overall_score', design_result.get('quality_score', 0)):.0f}/100")

    # Show ADRs
    adrs = arch.get("adrs", [])
    if adrs:
        print("\n  Architecture Decision Records:")
        for adr in adrs:
            print(f"    {adr.get('title', '')}: {adr.get('decision', '')}")

    # ═══════════════════════════════════════════
    # D4: PROTOTYPE
    # ═══════════════════════════════════════════
    if skip_proto:
        print_step("D4", "PROTOTYPE — Skipped (--skip-prototype)")
    else:
        print_step("D4", "PROTOTYPE — Generating Next.js app (LIVE)")

        if not llm:
            print("  ERROR: No LLM available for prototype generation.")
            print("  Add ANTHROPIC_API_KEY to .env.local or use --skip-prototype")
        else:
            design_artifacts = []
            for key, name in [("architecture", "Architecture"), ("database_schema", "Schema"),
                               ("api_specification", "API"), ("auth_design", "Auth"),
                               ("frontend_components", "Frontend")]:
                data = design_outputs.get(key, {})
                if data:
                    design_artifacts.append({"name": name, "content": json.dumps(data, default=str)})

            understanding = disc_outputs.get("system_understanding", {})
            biz_summary = understanding.get("system_purpose", "")[:1000] if isinstance(understanding, dict) else ""

            from src.agents.prototype.agent import PrototypeWorkflow, create_initial_state as create_proto_state

            proto_state = create_proto_state(
                project_id=project_id, llm=llm, session=mock_session,
                design_artifacts=design_artifacts,
                business_context=[{"system_purpose": biz_summary}],
                preview_provider="local_dev",
            )
            proto_result = await PrototypeWorkflow().compile().ainvoke(proto_state)

            proto_outputs = proto_result.get("task_outputs", {})
            code = proto_outputs.get("prototype_code", {})
            validation = proto_outputs.get("validation", {})
            preview_url = proto_result.get("preview_url", "")

            file_tree = code.get("file_tree", {})
            print_kv("Files generated", len(file_tree))
            print_kv("Validation", "PASS" if validation.get("passed") else "WARNINGS")
            print_kv("Quality", f"{proto_result.get('quality_score', 0):.0f}/100")

            if preview_url:
                print(f"\n  PREVIEW URL: {preview_url}")
            elif file_tree:
                out_dir = Path.home() / ".d8x" / "previews" / "d8x-demo"
                out_dir.mkdir(parents=True, exist_ok=True)
                for fp, content in file_tree.items():
                    (out_dir / fp).parent.mkdir(parents=True, exist_ok=True)
                    (out_dir / fp).write_text(content)
                if code.get("package_json"):
                    (out_dir / "package.json").write_text(code["package_json"])
                print(f"\n  Prototype written to: {out_dir}")
                print(f"  To run: cd {out_dir} && npm install --legacy-peer-deps && npx next dev --port 3100")

    # ═══════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════
    elapsed = time.time() - start
    print_header("DEMO COMPLETE")
    print_kv("Total time", f"{elapsed:.0f}s ({elapsed/60:.1f} min)")
    print_kv("Mode", mode)
    print_kv("Business rules", len(rules))
    print_kv("Domain entities", len(entities))
    print_kv("DB tables", len(schema.get("tables", [])))
    print_kv("API endpoints", len(api.get("endpoints", [])))
    print()


if __name__ == "__main__":
    asyncio.run(main())
