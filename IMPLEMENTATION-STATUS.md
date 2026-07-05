# D8X — Implementation Status

> Last updated: 2026-05-09

## Pipeline Status

| Agent | Status | LLM Mode | Simulation Fallback |
|-------|--------|----------|---------------------|
| **D1: Ingest** | ✅ Working | Real LLM (file analysis) | ✅ Rule-based classification |
| **D2: Discover** | ✅ Working | Real LLM (rule extraction, conflict/vulnerability detection) | ✅ Scenario-based simulation |
| **D3: Design** | ✅ Working | Real LLM (architecture, schema, API, auth, frontend) | ✅ Scenario-based simulation |
| **D4: Prototype** | ✅ Working | Simulation only | ✅ Hardcoded output |
| **D5: Plan** | 🔨 Skeleton | — | — |
| **D6: Build** | 🔨 Skeleton | — | — |
| **D7: Test** | 🔨 Skeleton | — | — |
| **D8: Ship** | 🔨 Skeleton | — | — |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      MISSION CONTROL (Next.js 14)                │
│  dashboard/  — Tailwind + shadcn/ui + React Query               │
│  Routes: /projects, /projects/new, /projects/[id]               │
│  Features: Pipeline visualization, agent reports, approval UI   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (React Query polling)
┌──────────────────────────────▼──────────────────────────────────┐
│                      FASTAPI BACKEND (:8000)                     │
│  src/api/  — Routes, schemas, services                          │
│  Endpoints: /api/projects, /api/projects/{id}/agents/*,         │
│             /api/projects/{id}/approvals/*                       │
└──────────────┬────────────────────────────┬─────────────────────┘
               │                            │
┌──────────────▼──────────┐  ┌──────────────▼─────────────────────┐
│   LLM PROVIDERS          │  │   DATABASE + STORAGE               │
│   src/tools/llm.py       │  │   PostgreSQL 16 + pgvector         │
│                          │  │   MinIO (S3-compatible)             │
│   Fallback chain:        │  │   Redis                            │
│   Google → Groq →        │  │                                    │
│   Cerebras → OpenRouter  │  │   Tables: projects, agent_runs,    │
│   → Ollama (local)       │  │   artifacts, approval_gates,       │
│                          │  │   business_context (vector 1536),  │
│   All via OpenAI SDK     │  │   conversations, epics,            │
│   (compatible endpoints) │  │   user_stories, error_reports      │
└──────────────────────────┘  └────────────────────────────────────┘
```

## LLM Provider Configuration

| Provider | Model | Use Case | Speed |
|----------|-------|----------|-------|
| **Google AI Studio** | gemini-2.5-flash | Primary (default) | ~2-5s per call |
| **Groq** | llama-3.3-70b-versatile | Fallback #1 | ~1-3s |
| **Cerebras** | llama-3.3-70b | Fallback #2 | ~1-2s |
| **OpenRouter** | google/gemini-2.5-flash-preview | Fallback #3 | ~3-5s |
| **Ollama** | qwen2.5-coder:14b/32b | Local fallback | 10-60s |

Config in `.env`:
```
LLM_PROVIDER=google
GOOGLE_AI_KEY=...
GROQ_API_KEY=...
CEREBRAS_API_KEY=...
OPENROUTER_API_KEY=...
```

Per-agent overrides supported:
```
INGEST_LLM_PROVIDER=groq      # fast, for file classification
DISCOVER_LLM_PROVIDER=google  # quality, for rule extraction
DESIGN_LLM_PROVIDER=google    # quality, for architecture
```

## What Each Agent Does (Current Implementation)

### D1: Ingest (`src/api/routes/agents.py` → `_run_ingest_agent`)

1. Reads uploaded `Artifact` records from DB
2. Classifies files (rule-based: `simulation_data.classify_file()`)
3. Computes quality score (file diversity, volume, type coverage)
4. **Stores actual file content** in `business_context` table (category: `ingested_source`)
5. **Runs LLM analysis** (`src/agents/ingest/llm_analysis.py`):
   - Detects project type (greenfield vs legacy modernization)
   - Identifies industry domain
   - Per-file assessment (document type, key topics, importance, summary)
   - Overall readiness assessment with gaps and suggestions
6. Creates approval gate

### D2: Discover (`src/api/routes/agents.py` → `_run_discover_agent`)

1. Reads `ingested_source` entries from `business_context`
2. **Phase 1**: Per-document extraction (LLM) — business rules, entities, AND defects/vulnerabilities
3. **Phase 2**: Cross-source conflict detection (LLM) — security vulnerabilities, logic bugs, compliance violations, data conflicts, implementation gaps
4. **Phase 3**: Clarification question generation (LLM)
5. **Phase 4**: System understanding synthesis (LLM)
6. **Phase 5**: Quality scoring (computed from extraction results)
7. Stores all results in `business_context` (categories: `business_rule`, `domain_entity`, `conflict`)
8. Creates approval gate
9. Falls back to simulation data if LLM fails

**Key file**: `src/agents/discover/llm_discovery.py`

### D3: Design (`src/api/routes/agents.py` → `_run_design_simulation`)

1. Reads all `business_context` (rules, entities, conflicts, sources)
2. **Phase 1**: Architecture & tech stack (LLM) — evaluates alternatives, makes justified choices based on actual requirements
3. **Phase 2**: Database schema (LLM) — tables, columns, encryption strategy
4. **Phase 3**: API specification (LLM) — endpoints, pagination, versioning
5. **Phase 4**: Auth design (LLM) — roles, permissions, compliance features
6. **Phase 5**: Frontend design (LLM) — pages, components, state management
7. Stores ADRs and tech stack choices in `business_context` (categories: `architecture_decision`, `tech_stack_choice`)
8. Creates approval gate
9. Falls back to simulation data if LLM fails

**Key principle**: NO hardcoded tech assumptions. The LLM reads the actual documents and chooses technology based on:
- Team skills mentioned in docs
- Compliance requirements (HIPAA, PCI DSS)
- Cloud agreements mentioned in meeting notes
- Migration path from existing systems
- Budget constraints

**Key file**: `src/agents/design/llm_design.py`

### D4: Prototype (`src/api/routes/agents.py` → `_run_prototype_simulation`)

Currently simulation-only. Produces hardcoded output (47 files, preview URL).

**TODO**: Read D3's architecture decisions from `business_context` and generate prototype in the chosen frontend framework.

## Dashboard (Frontend)

### Tech Stack
- Next.js 14 (App Router with route groups)
- TypeScript
- Tailwind CSS + shadcn/ui
- React Query (polling every 30s when agent running)
- Axios API client

### Key Components

| Component | Purpose |
|-----------|---------|
| `pipeline-bar.tsx` | 8-stage visual pipeline with status-driven styling |
| `agent-detail-panel.tsx` | Routes to correct report based on agent type |
| `ingest-report.tsx` | D1 report: files table, quality assessment, LLM analysis |
| `discover-report.tsx` | D2 report: security vulnerabilities, bugs, conflicts, rules, entities, questions |
| `design-report.tsx` | D3 report: architecture diagram, ADRs with alternatives, schema, API, auth |
| `approval-actions.tsx` | Approve/Revise/Reject + auto-starts next agent |
| `file-uploader.tsx` | Drag-drop upload with file type detection |

### Auto-Start Flow (After Approval)

1. Frontend calls `decideApproval()` → backend creates PENDING run for next agent
2. Frontend calls `startAgent(nextType)` → backend finds PENDING run and starts it
3. Frontend hard-navigates to new run URL

## API Endpoints

### Projects
- `POST /api/projects/` — Create project
- `GET /api/projects/` — List projects
- `GET /api/projects/{id}` — Get project
- `GET /api/projects/{id}/runs` — List all runs
- `GET /api/projects/{id}/artifacts` — List artifacts

### Agents
- `POST /api/projects/{id}/agents/ingest/start` — Start D1
- `POST /api/projects/{id}/agents/discovery/start` — Start D2
- `POST /api/projects/{id}/agents/design/start` — Start D3
- `POST /api/projects/{id}/agents/prototype/start` — Start D4
- `GET /api/projects/{id}/agents/{run_id}/status` — Poll agent status
- `GET /api/projects/{id}/agents/latest` — Get latest run

### Approvals
- `GET /api/projects/{id}/approvals/` — List gates
- `POST /api/projects/{id}/approvals/{gate_id}/decide` — Approve/reject/revise

### Upload
- `POST /api/projects/{id}/ingest/upload` — Upload files (multipart)

## File Structure (Key Files)

```
src/
├── config.py                           # Settings (LLM keys, DB, etc.)
├── tools/
│   └── llm.py                          # Multi-provider LLM factory
├── agents/
│   ├── ingest/llm_analysis.py          # D1 LLM file analysis
│   ├── discover/llm_discovery.py       # D2 LLM rule/vulnerability extraction
│   └── design/llm_design.py           # D3 LLM architecture generation
├── api/
│   ├── routes/
│   │   ├── agents.py                   # Agent runners + start endpoints
│   │   ├── approvals.py               # Approval decisions + auto-start
│   │   ├── ingest.py                  # File upload
│   │   └── projects.py               # CRUD + runs/artifacts
│   ├── schemas/project.py            # Pydantic request/response models
│   └── services/simulation_data.py   # Simulation fallback data
├── context_store/
│   ├── models.py                      # SQLAlchemy ORM models
│   ├── database.py                    # Async engine + sessions
│   └── repository.py                  # BusinessContext CRUD + vector search
└── orchestrator/
    └── approval.py                    # Approval gate logic + phase transitions

dashboard/
├── src/app/(dashboard)/projects/[id]/page.tsx   # Project detail + pipeline
├── src/components/dashboard/                     # All report components
├── src/lib/api-client.ts                        # Typed API calls
└── src/lib/hooks/                               # React Query hooks
```

## Running the System

```bash
# Prerequisites: PostgreSQL + MinIO running (Docker or local)

# Backend
uv run uvicorn src.api.main:app --reload --port 8000

# Frontend
cd dashboard && npm run dev

# Open: http://localhost:3000/projects/new
```

## Known Issues / TODO

- [ ] D4 Prototype still uses simulation — needs to read D3's chosen frontend stack
- [ ] D5-D8 are skeleton only
- [ ] No real embeddings stored (embedding_provider=fake in dev)
- [ ] Background task auto-start from approval endpoint unreliable (using frontend-initiated start as workaround)
- [ ] Report PDF/DOCX download implemented but not tested end-to-end
- [ ] No authentication on the dashboard
