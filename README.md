# Agentic SDLC Workflow Platform

Multi-agent AI system that automates the entire Software Development Life Cycle: from legacy application analysis through modernized deployment.

## Architecture

Six specialized AI agents orchestrated by LangGraph:

1. **Discovery Agent** — Analyzes legacy docs, videos, source code, BRDs
2. **Design Agent** — Creates system design for the modernized application
3. **Prototyping Agent** — Builds interactive prototype with feedback loops
4. **Planning Agent** — Generates detailed step-by-step MVP implementation plan
5. **Implementation Agent** — Writes production code, commits to GitHub, creates PRs
6. **Deployment Agent** — Deploys to environments, monitors logs, reports errors

All agents share a Business Context Store (PostgreSQL + pgvector) except the Deployment Agent.

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M4 Max recommended)
- Python 3.12+ (via Homebrew)
- Docker Desktop
- uv (`brew install uv`)
- Claude Code (`curl -fsSL https://claude.ai/install.sh | bash`)

### Setup

```bash
# Clone and enter project
cd ~/documents/projects/agentic-claude

# Install Python dependencies
uv sync
uv sync --extra dev

# Copy env file and add your API keys
cp .env.example .env

# Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d

# Verify everything works
chmod +x scripts/verify-setup.sh
./scripts/verify-setup.sh

# Run smoke test (requires API keys in .env)
uv run python scripts/smoke_test.py

# Start the API server
uv run uvicorn src.api.main:app --reload --port 8000
```

### Using Claude Code

```bash
cd ~/documents/projects/agentic-claude
claude
```

Claude Code reads `CLAUDE.md` automatically and understands the full project context.

## Project Structure

```
├── CLAUDE.md                  # Claude Code project context (auto-loaded)
├── .claude/commands/          # Custom slash commands for Claude Code
├── src/
│   ├── agents/                # Agent modules
│   ├── orchestrator/          # LangGraph workflow engine
│   ├── api/                   # FastAPI backend
│   ├── tools/                 # Shared agent tools
│   └── context_store/         # Database models and queries
├── dashboard/                 # Next.js frontend
├── infra/docker/              # Docker Compose + DB init
├── tests/                     # Test suites
└── scripts/                   # Utility scripts
```

## Services (Docker Compose)

| Service    | Port  | URL                          |
|------------|-------|------------------------------|
| PostgreSQL | 5432  | `localhost:5432`             |
| Redis      | 6379  | `localhost:6379`             |
| MinIO      | 9000  | `http://localhost:9001`      |
| Grafana    | 3001  | `http://localhost:3001`      |
| Loki       | 3100  | `http://localhost:3100`      |
| FastAPI    | 8000  | `http://localhost:8000/docs` |

## License

Private — All rights reserved.
