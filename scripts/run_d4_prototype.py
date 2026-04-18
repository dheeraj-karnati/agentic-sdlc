"""D4 Prototype generator — streamlined for local Ollama models.

Reads cached D3 Design output and generates a Next.js prototype
using simplified prompts that work well with 32b models.

Usage:
    uv run python scripts/run_d4_prototype.py
    uv run python scripts/run_d4_prototype.py --claude   # use Claude API instead
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures" / "cached_pipeline"
OUTPUT_DIR = Path.home() / ".d8x" / "previews" / "taskflow"


async def main() -> None:
    start = time.time()
    use_claude = "--claude" in sys.argv

    # Load API keys
    from dotenv import load_dotenv
    env_local = Path(__file__).parent.parent / ".env.local"
    if env_local.exists():
        load_dotenv(env_local, override=True)

    if use_claude:
        import src.config
        from src.config import Settings
        src.config.settings = Settings()
        from src.tools.llm import get_llm
        llm = get_llm(max_tokens=8192)
        print("LLM: Claude API")
    else:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model="qwen2.5-coder:32b",
            base_url="http://localhost:11434",
            num_predict=8192,
            keep_alive="30m",
            timeout=600,
            format="json",
        )
        print("LLM: Ollama qwen2.5-coder:32b (local, free)")

    # Load cached design
    design = json.loads((FIXTURES / "d3_design.json").read_text())
    design_outputs = design["task_outputs"]
    discover = json.loads((FIXTURES / "d2_discover.json").read_text())
    disc_outputs = discover["task_outputs"]

    arch = design_outputs.get("architecture", {})
    schema = design_outputs.get("database_schema", {})
    api = design_outputs.get("api_specification", {})
    frontend = design_outputs.get("frontend_components", {})

    print(f"Design: {arch.get('pattern')} | {len(schema.get('tables',[]))} tables | {len(api.get('endpoints',[]))} endpoints | {len(frontend.get('routes',[]))} pages")

    # ─── Step 1: Generate prototype spec (simplified prompt) ───
    print("\n[1/3] Interpreting design into prototype spec...")

    from langchain_core.messages import HumanMessage, SystemMessage

    # Build a concise summary instead of dumping full JSON
    pages_summary = "\n".join(f"  - {r.get('path','/')} → {r.get('page_component','Page')}" for r in frontend.get("routes", []))
    tables_summary = "\n".join(f"  - {t['name']}: {', '.join(c.get('name','') for c in t.get('columns',[])[:5])}" for t in schema.get("tables", [])[:8])
    api_summary = "\n".join(f"  - {e.get('method','GET')} {e.get('path','/')}: {e.get('summary','')}" for e in api.get("endpoints", [])[:12])
    roles = ", ".join(r.get("name", "") for r in design_outputs.get("auth_design", {}).get("roles", []))

    spec_prompt = f"""Generate a prototype spec for a project management app called TaskFlow.

Pages:
{pages_summary}

Database tables:
{tables_summary}

Key API endpoints:
{api_summary}

User roles: {roles}

Return JSON with:
- pages: list of {{route, title, components (list of component names)}}
- mock_data: list of {{entity, records (list of 3 realistic sample records as dicts)}}
- navigation: list of {{label, route, icon (emoji)}}"""

    t1 = time.time()
    resp = await llm.ainvoke([
        SystemMessage(content="You are a frontend architect. Return valid JSON only."),
        HumanMessage(content=spec_prompt),
    ])
    from src.tools.json_utils import parse_llm_json
    spec = parse_llm_json(resp.content)  # type: ignore[arg-type]
    print(f"  Done ({time.time()-t1:.0f}s) — {len(spec.get('pages',[]))} pages, {len(spec.get('mock_data',[]))} data models")

    # ─── Step 2: Generate Next.js code (simplified prompt) ───
    print("\n[2/3] Generating Next.js application...")

    # Only send the spec (small), not the full design
    pages_list = spec.get("pages", [])
    mock_data = spec.get("mock_data", [])
    nav = spec.get("navigation", [])

    code_prompt = f"""Generate a Next.js 14 App Router application for TaskFlow (project management).

Requirements:
- {len(pages_list)} pages: {', '.join(p.get('route','') for p in pages_list)}
- Navigation sidebar with: {', '.join(n.get('label','') for n in nav)}
- Use Tailwind CSS for styling (dark theme, professional look)
- Include mock data inline (no API calls needed)
- TypeScript, functional components

Return JSON with:
- file_tree: dict mapping file paths to file contents. Include:
  - src/app/layout.tsx (with sidebar navigation)
  - src/app/page.tsx (redirect to /dashboard)
  - src/app/globals.css (tailwind imports + dark theme)
  - One page.tsx for each route under src/app/[route]/page.tsx
- package_json: valid package.json string with next, react, react-dom, tailwindcss, autoprefixer, postcss, typescript, @types/react, @types/node
- total_files: number of files

Mock data to include:
{json.dumps(mock_data[:3], indent=2, default=str)[:2000]}

IMPORTANT: Each file content must be a complete, valid TypeScript/React file. Use 'use client' for interactive components."""

    t2 = time.time()
    resp = await llm.ainvoke([
        SystemMessage(content="You are a senior Next.js developer. Return valid JSON only. The file_tree values must be complete file contents as strings."),
        HumanMessage(content=code_prompt),
    ])
    code = parse_llm_json(resp.content)  # type: ignore[arg-type]
    file_tree = code.get("file_tree", {})
    pkg_json = code.get("package_json", "")
    print(f"  Done ({time.time()-t2:.0f}s) — {len(file_tree)} files generated")

    if not file_tree:
        print("\n  ERROR: No files generated. The model may have run out of output tokens.")
        print("  Try: uv run python scripts/run_d4_prototype.py --claude")
        return

    # ─── Step 3: Write to disk ───
    print(f"\n[3/3] Writing prototype to {OUTPUT_DIR}")

    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    for fp, content in file_tree.items():
        file_path = OUTPUT_DIR / fp
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(str(content))
        print(f"  {fp}")

    # Write package.json
    if pkg_json:
        pkg_path = OUTPUT_DIR / "package.json"
        if not pkg_path.exists():
            if isinstance(pkg_json, str):
                pkg_path.write_text(pkg_json)
            else:
                pkg_path.write_text(json.dumps(pkg_json, indent=2))

    # Write configs if missing
    configs = {
        "next.config.mjs": '/** @type {import("next").NextConfig} */\nconst config = {};\nexport default config;\n',
        "tsconfig.json": '{"compilerOptions":{"target":"ES2017","lib":["dom","dom.iterable","esnext"],"allowJs":true,"skipLibCheck":true,"strict":false,"noEmit":true,"esModuleInterop":true,"module":"esnext","moduleResolution":"bundler","resolveJsonModule":true,"isolatedModules":true,"jsx":"preserve","incremental":true,"plugins":[{"name":"next"}],"paths":{"@/*":["./src/*"]}},"include":["next-env.d.ts","**/*.ts","**/*.tsx",".next/types/**/*.ts"],"exclude":["node_modules"]}',
        "tailwind.config.ts": 'import type { Config } from "tailwindcss";\nconst config: Config = { content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"], theme: { extend: {} }, plugins: [] };\nexport default config;\n',
        "postcss.config.mjs": 'const config = { plugins: { tailwindcss: {}, autoprefixer: {} } };\nexport default config;\n',
    }
    for name, content in configs.items():
        p = OUTPUT_DIR / name
        if not p.exists():
            p.write_text(content)

    # Ensure globals.css exists
    globals_css = OUTPUT_DIR / "src" / "app" / "globals.css"
    if not globals_css.exists():
        globals_css.parent.mkdir(parents=True, exist_ok=True)
        globals_css.write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n\nbody { @apply bg-gray-950 text-white; }\n")

    elapsed = time.time() - start
    print(f"\n{'=' * 50}")
    print(f"  PROTOTYPE GENERATED in {elapsed:.0f}s")
    print(f"  Files: {len(file_tree)}")
    print(f"  Location: {OUTPUT_DIR}")
    print(f"")
    print(f"  To run:")
    print(f"    cd {OUTPUT_DIR}")
    print(f"    npm install --legacy-peer-deps")
    print(f"    npx next dev --port 3100")
    print(f"    # Open http://localhost:3100")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())
