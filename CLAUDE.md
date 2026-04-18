# D8X — Agentic SDLC Platform

## Strategic Context (READ FIRST)

**What D8X is:** A multi-agent AI platform that automates SDLC work
(requirements analysis → architecture → planning → code → test → deploy)
with human-in-the-loop approval gates at every stage.

**Who buys it (first 12 months):** Mid-market consulting firms
(10-200 people) doing SDLC work for enterprise clients. NOT FAANG.
NOT large enterprise. NOT solo developers. Consulting firms have
the exact pain D8X solves — their architects spend 40+ hours per
week doing manual requirements analysis.

**Primary competitive moat:** Cross-source conflict detection.
No other tool finds contradictions between a BRD, Python code,
and meeting notes automatically. This is D8X's patent claim and
the #1 reason customers buy.

**Hero agent:** D2: Discover. All other agents support D2 as
either upstream (Ingest) or downstream (Design, Plan, Build).
When in doubt about priorities, ask: "Does this make D2 Discover
better?"

**What we DON'T build:**
- A better code editor (Cursor wins there)
- A better document parser (Unstructured.io wins there)
- A better CI/CD tool (GitHub Actions wins there)
- Our own LLM or fine-tuned model (pointless at our stage)
- Mobile apps (web-only until we have 50+ customers)
- On-premise deployment (SaaS-only until enterprise tier)

**What we DO build:**
- Agent orchestration with shared context between stages
- Requirements-to-architecture traceability
- Cross-source conflict detection (D2)
- HITL approval gates with audit trails
- Format adapters (Jira, Confluence first) that let customers
  use D8X with their existing tools

**Decision framework:** When choosing between two implementation
options, pick the one that:
1. Works for a consulting firm selling D8X services to their clients
2. Improves D2: Discover quality
3. Makes each agent independently usable (not just in the full pipeline)
4. Reduces time-to-first-value for a new customer
5. Scales to 100 tenants without architectural rewrite

**Current stage:** Building simulation-first, then real LLM integration,
then production hardening. We are NOT ready for real customers yet.

**Timeline to revenue:** 6 months from now. Bootstrap budget,
6-12 month runway.

## Architectural Principles (non-negotiable)

1. **Multi-tenancy from day one** — every query, every LLM call,
   every file upload scoped to a tenant. Never build single-tenant
   then retrofit.

2. **Each agent independently usable** — Customers can call D2
   directly via API without running D1 first. Format adapters
   normalize their input.

3. **Shared Business Context Store** — All agents read from and
   write to the same pgvector store. This is how D3 knows what
   D2 found. This is how traceability works.

4. **Observability is a product feature** — Every LLM call traced.
   Every agent decision explainable. Customer should see: "D8X
   recommended X because of these 5 rules, here's the prompt,
   here's the response, here's the confidence score."

5. **Version everything** — Business rules change. Designs iterate.
   Every artifact versioned with lineage (which upstream artifacts
   it was derived from).

6. **Simulation fallback** — Every agent has both a real LLM
   implementation and a simulation fallback. If LLM fails,
   simulation runs. Demos never break.

## About

D8X is a multi-agent AI system that automates the full SDLC pipeline through 8 specialized agents:

**D1: Ingest** → **D2: Discover** → **D3: Design** → **D4: Prototype** → **D5: Plan** → **D6: Build** → **D7: Test** → **D8: Ship**

| Agent | Purpose |
|-------|---------|
| **D1: Ingest** | Parse any input format (PDFs, DOCX, code, audio, video, images) into structured text |
| **D2: Discover** | Extract requirements, business rules, entities, conflicts from ingested content |
| **D3: Design** | Generate architecture, database schema, API contracts, auth, frontend design |
| **D4: Prototype** | Interactive demo with stakeholder feedback loop |
| **D5: Plan** | Epics, sequenced user stories, detailed acceptance criteria |
| **D6: Build** | Story-by-story code generation, GitHub PRs |
| **D7: Test** | QA, security scans, accessibility, coverage, acceptance verification |
| **D8: Ship** | Deploy, monitor logs, error feedback to Build |

All agents are orchestrated by LangGraph with human-in-the-loop approval gates between every phase. All agents share a Business Context Store (PostgreSQL + pgvector). Test has a feedback loop back to Build on QA failure. Ship has a feedback loop back to Build on deploy errors.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async with asyncpg)
- **AI/ML:** LangChain, LangGraph, Anthropic Claude API, Ollama (local LLMs)
- **Frontend Dashboard:** Next.js 14+, TypeScript, Tailwind CSS, shadcn/ui
- **Database:** PostgreSQL 16 + pgvector (HNSW index, cosine similarity, 1536-dim embeddings)
- **Queue:** Redis Streams
- **Object Storage:** MinIO (S3-compatible)
- **Monitoring:** Grafana + Loki + Promtail
- **CI/CD:** GitHub Actions
- **Package Manager:** uv (Python), npm (dashboard)
- **Infrastructure:** Docker Compose on remote iMac (PostgreSQL, Redis, MinIO, Ollama)

## Project Structure

```
├── CLAUDE.md
├── pyproject.toml
├── .env / .env.example
├── src/
│   ├── config.py                          # Pydantic Settings, all config from .env
│   ├── agents/
│   │   ├── base/                          # ★ BASE FRAMEWORK - all agents extend these
│   │   │   ├── skill.py                   # BaseSkill: stateless, reusable capability
│   │   │   ├── task.py                    # BaseTask: focused work unit with prompt + schema
│   │   │   └── workflow.py                # BaseWorkflow: LangGraph StateGraph wrapper
│   │   ├── ingest/                        # D1: Parse any input format
│   │   │   ├── agent.py                   # IngestWorkflow
│   │   │   ├── skills/                    # audio_transcription, document_parsing, code_parsing, etc.
│   │   │   └── tasks/                     # ingest_files, classify_and_structure, etc.
│   │   ├── discover/                      # D2: Extract requirements, rules, entities
│   │   │   ├── agent.py                   # DiscoverWorkflow
│   │   │   ├── skills/                    # code_analysis, doc_extraction, etc.
│   │   │   └── tasks/                     # parse_classify, deep_analysis, etc.
│   │   ├── design/                        # D3: Architecture, schema, API, auth, frontend
│   │   │   ├── agent.py                   # DesignWorkflow
│   │   │   ├── skills/                    # architecture_decision, schema_design, etc.
│   │   │   └── tasks/                     # generate_architecture, generate_data_model, etc.
│   │   ├── prototype/                     # D4: Interactive demo
│   │   ├── plan/                          # D5: Epics + user stories
│   │   ├── build/                         # D6: Code generation + GitHub PRs
│   │   ├── test/                          # D7: QA, security, acceptance verification
│   │   │   ├── agent.py                   # TestWorkflow (skeleton)
│   │   │   ├── skills/                    # e2e_test_generation, security_scanning, etc.
│   │   │   └── tasks/                     # generate_test_suites, run_security_scan, etc.
│   │   └── ship/                          # D8: Deploy + monitoring
│   ├── orchestrator/
│   │   ├── pipeline.py                    # Main LangGraph pipeline (chains all agents)
│   │   └── approval.py                    # Approval gate system
│   ├── api/
│   │   ├── main.py                        # FastAPI app entry point
│   │   ├── routes/                        # Route modules (projects, agents, approvals, plan)
│   │   └── schemas/                       # Pydantic request/response models
│   ├── tools/
│   │   ├── llm.py                         # ★ get_llm() and get_embeddings() factories
│   │   └── embeddings.py                  # Chunking + embedding utilities
│   └── context_store/
│       ├── database.py                    # Async engine + session factory
│       ├── models.py                      # SQLAlchemy ORM models
│       └── repository.py                  # Business context CRUD + vector search
├── dashboard/                             # Next.js frontend
├── infra/docker/                          # Docker Compose + init-db.sql
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── scripts/
    ├── verify-setup.sh
    └── smoke_test.py
```

## Commands

```bash
# Development
uv run uvicorn src.api.main:app --reload --port 8000    # FastAPI server
uv run pytest tests/ -v                                  # All tests
uv run pytest tests/unit/ -v --tb=short                  # Unit tests only
uv run pytest tests/unit/test_discover_skills.py -v     # Specific test file
uv run ruff check src/                                   # Lint
uv run ruff format src/                                  # Format
uv run mypy src/                                         # Type check

# Infrastructure (runs on remote iMac)
docker compose -f infra/docker/docker-compose.yml up -d
docker compose -f infra/docker/docker-compose.yml down

# Dashboard
cd dashboard && npm run dev
```

## Architecture: Workflow → Task → Skill Pattern

Every agent follows this three-layer architecture. This is the most important pattern in the codebase.

### Skills (src/agents/base/skill.py)
- **Stateless, reusable, independently testable** capabilities
- Each skill has a Pydantic `InputModel` and `OutputModel`
- Skills do ONE thing well: parse code, extract entities, detect conflicts
- Skills are shared across agents (e.g., entity_extraction used by both Discovery and Design)
- Include retry logic with tenacity (3 retries, exponential backoff)
- NEVER call the database or manage state — that's the workflow's job

```python
# Pattern for creating a new skill
class MySkill(BaseSkill):
    name = "my_skill"
    description = "What this skill does"
    input_model = MySkillInput    # Pydantic model
    output_model = MySkillOutput  # Pydantic model

    async def execute(self, input_data: MySkillInput) -> MySkillOutput:
        # Do the work, return typed output
        ...
```

### Tasks (src/agents/base/task.py)
- **Focused units of work** that combine a prompt template + LLM call + output validation
- Each task has: input_schema, output_schema, prompt_template, few_shot_examples, validation_fn
- Tasks invoke skills as needed
- Tasks handle LLM output parsing and retry with corrective feedback
- Few-shot examples are CRITICAL — they show the LLM what "good" output looks like

```python
# Pattern for creating a new task
class MyTask(BaseTask):
    name = "my_task"
    input_schema = MyTaskInput
    output_schema = MyTaskOutput
    prompt_template = """..."""
    few_shot_examples = [
        {"input": ..., "output": ...},  # Show good examples
    ]

    def validate(self, output: MyTaskOutput) -> bool:
        # Custom validation logic
        ...
```

### Workflows (src/agents/base/workflow.py)
- **LangGraph StateGraph** that orchestrates tasks in sequence
- Manages state, HITL interrupts, approval gates, quality checks
- Handles database persistence (storing results, creating artifacts)
- One workflow per agent

```python
# Pattern for creating a new agent workflow
class MyAgentWorkflow(BaseWorkflow):
    def build_graph(self) -> StateGraph:
        graph = StateGraph(MyAgentState)
        graph.add_node("task_1", self.run_task_1)
        graph.add_node("task_2", self.run_task_2)
        graph.add_node("quality_gate", self.assess_quality)
        # ... edges and conditions
        return graph
```

## Code Style & Conventions

### Python
- Type hints required on ALL functions and methods — no exceptions
- Use Pydantic v2 models for ALL data structures (input/output schemas, API payloads, config)
- Use async/await for ALL database operations and API endpoints
- SQLAlchemy 2.0 style: `mapped_column`, async sessions, `select()` not legacy query
- Functions should be small and focused (< 50 lines). If longer, decompose.
- Prefer composition over inheritance
- Use dependency injection: database sessions, LLM clients, and services are injected, not imported globally

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Skills: `{name}_skill.py` with class `{Name}Skill`
- Tasks: `{name}_task.py` with class `{Name}Task`
- Pydantic models: `{Name}Input`, `{Name}Output`, `{Name}Response`, `{Name}Create`

### Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Feature branches: `feat/discover-skills`, `fix/enum-case-mismatch`
- Always create a branch before making changes. Never commit directly to main.

### Error Handling
- API routes return structured error responses, never raw exceptions
- Use HTTPException with appropriate status codes and detail messages
- Tasks handle LLM failures gracefully: retry with corrective feedback, then fail with clear error
- Log errors with context (project_id, agent_type, task_name) using structured logging

## LLM Usage

### Factory Functions (src/tools/llm.py)
Always use `get_llm()` and `get_embeddings()` — never instantiate LLM clients directly.

```python
from src.tools.llm import get_llm, get_embeddings

llm = get_llm()                    # Uses LLM_PROVIDER from .env
llm = get_llm(provider="anthropic") # Force cloud for quality-critical tasks
embeddings = get_embeddings()       # Local by default (nomic-embed-text)
```

### When to Use Which Provider
- `local` (Ollama on iMac): Day-to-day development, testing workflows, embeddings (always)
- `anthropic` (Claude API): Plan Agent tasks, quality assessment, production runs, any task where output quality is critical

### Prompt Engineering Rules
- Every task prompt must include: role/context, specific instruction, output format (as JSON schema), and at least 2 few-shot examples
- Few-shot examples should show the DIFFERENCE between shallow and deep output
- Include explicit instructions about what NOT to do (e.g., "Do not write vague one-line descriptions. Each business rule must include trigger condition, action, exceptions, and validation logic.")
- When output fails validation, retry with: "Your previous output failed validation because: {reason}. Here was your output: {output}. Please fix the following issues and try again: {specific_issues}"

## Database

### Connection
- Async driver: `postgresql+asyncpg://` (for application code)
- Sync driver: `postgresql://` (for Alembic migrations and scripts)
- All DB access goes through repository classes, never raw SQL in routes

### Tables (key ones)
- `projects` — top-level entity, tracks current phase via `status` enum
- `agent_runs` — each agent execution, tracks status and token usage
- `artifacts` — generated files/documents, versioned, stored in MinIO
- `approval_gates` — HITL checkpoints between phases
- `conversations` — agent ↔ user Q&A exchanges
- `business_context` — accumulated knowledge with vector embeddings (1536-dim)
- `epics` — feature groupings generated by Plan Agent
- `user_stories` — detailed stories with ACs, schema changes, API specs, UI specs
- `error_reports` — monitoring agent findings

### Conventions
- UUID primary keys (`gen_random_uuid()`)
- TIMESTAMPTZ with `DEFAULT NOW()` for all timestamps
- JSONB for flexible/extensible data
- Enum types created in PostgreSQL (init-db.sql), referenced with `create_type=False` in SQLAlchemy
- Enum values are LOWERCASE in PostgreSQL — use `values_callable=lambda x: [e.value for e in x]` on all Enum columns

### Vector Search
```python
# Pattern for similarity search
from pgvector.sqlalchemy import Vector
from sqlalchemy import text

# Store embedding
entry.embedding = embedding_vector  # list[float], 1536 dimensions

# Search similar
results = await session.execute(
    select(BusinessContext)
    .where(BusinessContext.project_id == project_id)
    .order_by(BusinessContext.embedding.cosine_distance(query_embedding))
    .limit(5)
)
```

## API Design

### Route Structure
- `POST /api/projects/` — Create project
- `GET /api/projects/{id}` — Get project
- `POST /api/projects/{id}/agents/{type}/start` — Start an agent
- `GET /api/projects/{id}/agents/{run_id}/status` — Agent status
- `POST /api/projects/{id}/agents/{run_id}/respond` — Answer agent questions
- `POST /api/projects/{id}/agents/{run_id}/feedback` — Submit feedback
- `GET /api/projects/{id}/approvals` — List approval gates
- `POST /api/projects/{id}/approvals/{gate_id}/decide` — Approve/reject
- `GET /api/projects/{id}/epics` — List epics with stories
- `PUT /api/projects/{id}/stories/{story_id}` — PO edits a story
- `POST /api/projects/{id}/epics/{epic_id}/stories` — PO adds a story

### Conventions
- Routes are THIN — validate input, call service, return response
- Business logic lives in service classes or agent workflows
- Always return Pydantic response models
- Use FastAPI's `Depends()` for database sessions
- Pagination: `skip` and `limit` query params with sensible defaults

## Testing

### Structure
- `tests/unit/` — Test skills, tasks, schemas, and utilities in isolation. Mock LLM calls.
- `tests/integration/` — Test workflows end-to-end with database. Use transaction rollback.
- `tests/e2e/` — Test full API flows via httpx AsyncClient.

### Conventions
- Use `pytest` with `pytest-asyncio` (asyncio_mode = "auto")
- Mock LLM calls in unit tests — don't burn API credits
- For integration tests that need a database, use the running PostgreSQL instance
- Every new skill, task, and route MUST have corresponding tests
- Test both happy path and failure/edge cases

```python
# Pattern for testing a skill
async def test_my_skill():
    skill = MySkill()
    result = await skill.execute(MySkillInput(text="sample"))
    assert isinstance(result, MySkillOutput)
    assert len(result.findings) > 0

# Pattern for testing a task (mock LLM)
async def test_my_task(mocker):
    mock_llm = mocker.patch("src.tools.llm.get_llm")
    mock_llm.return_value.ainvoke.return_value = AIMessage(content='{"key": "value"}')
    task = MyTask()
    result = await task.execute(MyTaskInput(...))
    assert result.key == "value"
```

## Important Warnings

- NEVER commit `.env` files — only `.env.example`
- NEVER set `ANTHROPIC_API_KEY` as a shell environment variable — it conflicts with Claude Code Max subscription. Load it from `.env` in application code only via pydantic-settings.
- NEVER use `create_type=True` on SQLAlchemy Enum columns — enums are created by init-db.sql
- NEVER put business logic in route handlers — use service classes or task/skill pattern
- NEVER make a skill stateful or database-aware — skills are pure functions
- NEVER skip few-shot examples in task prompts — they are the #1 factor in output quality
- NEVER return unvalidated LLM output — always parse through a Pydantic model
- When PostgreSQL enums don't match Python enum values, the fix is `values_callable=lambda x: [e.value for e in x]`
- Infrastructure (PostgreSQL, Redis, MinIO, Ollama) runs on the remote iMac, not localhost. Connection strings are in `.env`.


## Decisions Log

Append-only. Newest at top. Use format:

### YYYY-MM-DD: Short title
**Context:** What triggered this decision  
**Decision:** What we chose  
**Why:** Reasoning  
**Alternatives rejected:** What we considered and why not  
**Revisit when:** Conditions that would reopen this decision

---

### 2026-04-18: Target consulting firms as first customer
**Context:** Choosing go-to-market strategy  
**Decision:** Mid-market consulting firms (10-200 people) as
first customer segment. Pricing: $2-10K/month per firm.  
**Why:** They have exact pain D8X solves, 2-4 week sales cycles,
willing to pilot new tools, provide great references.  
**Alternatives rejected:**
- FAANG (12-18 month sales cycles, need SOC 2, blacklist risk)
- Mid-market SaaS (harder pain to articulate)
- Solo developers (can't afford enterprise pricing)
  **Revisit when:** 10 consulting firm customers closed, ready for
  mid-market SaaS expansion.

### 2026-04-18: D2 Discover is the hero agent
**Context:** Limited engineering resources, can't perfect all 8 agents simultaneously  
**Decision:** Invest disproportionately in D2. Other agents support D2.  
**Why:** Cross-source conflict detection is our unique differentiator.
Patent claim is centered on this. Customer demos live and die on D2.  
**Alternatives rejected:**
- Equal investment across all agents (dilutes differentiation)
- Lead with D6 Build (commoditized, competes with Cursor/Devin)
  **Revisit when:** D2 quality score consistently > 85 across
  100+ test documents.

### 2026-04-18: Jira + Confluence as first integrations
**Context:** Format adapter prioritization  
**Decision:** Build Jira and Confluence adapters first.  
**Why:** 60%+ of enterprise customers use these. Same Atlassian
OAuth covers both. Consulting firm clients almost universally
have Jira.  
**Alternatives rejected:**
- Azure DevOps (Microsoft shops, smaller TAM)
- Notion (modern SaaS, newer market)
- Build all three in parallel (too much week-one scope)
  **Revisit when:** Jira + Confluence adapters complete and
  tested with 3+ real customer data sets.

### 2026-04-18: BackgroundTasks over Temporal for now
**Context:** Need durable agent execution  
**Decision:** FastAPI BackgroundTasks + DB-backed state  
**Why:** Works for < 100 concurrent runs. No cluster to operate.
Migration to Temporal is 1-week refactor when BaseAgent interface
is in place.  
**Alternatives rejected:**
- Temporal day-one (over-engineering for current scale)
- Dapr (cloud-native focus, over-engineered)
- Celery (older pattern, not async-first)
  **Revisit when:** 50+ concurrent agent runs, or agent runs
  exceed 1 hour duration.

### 2026-04-18: Free LLM providers for development and early customers
**Context:** Bootstrap budget, need demos to work  
**Decision:** Google Gemini 2.5 Flash (primary), Groq Llama
3.3 70B (fast), OpenRouter (fallback), Ollama (embeddings).  
**Why:** Zero cost during development. 1,500 req/day on Gemini
handles 50+ full pipeline runs per day.  
**Alternatives rejected:**
- Claude API from day one (expensive, not needed for simulation)
- Self-hosted LLM only (quality insufficient for D2)
  **Revisit when:** First paying customer signs. Then evaluate
  Claude Sonnet for quality-critical tasks (D2, D3).

### 2026-04-18: Simulation fallback for every agent
**Context:** LLM failures can't break demos  
**Decision:** Every agent has both real LLM implementation
and simulation fallback. If real fails, simulation runs.  
**Why:** Demos are too important to lose on API outages.
Development doesn't require constant LLM credit burn.  
**Alternatives rejected:**
- Real LLM only (too fragile for demos)
- Simulation only (not compelling for sales)
  **Revisit when:** Real LLM reliability reaches 99%+ and
  LLM API costs are covered by revenue.

### 2026-04-13: Provisional patent filed
**Context:** Protect IP before talking to investors/customers  
**Decision:** Filed provisional patent on D8X's cross-source
conflict detection with USPTO, $65 micro entity fee.  
**Why:** Establishes priority date. 12-month window to file
non-provisional.  
**Action required by:** December 2026 — file non-provisional
patent with patent attorney.

## What NOT To Do

This section exists because repeating these mistakes wastes time.
If Claude Code is about to do any of these, STOP and ask.

- **Don't build new parsers when Unstructured.io, PyMuPDF, or
  python-docx exists.** Wrap existing tools, don't rebuild them.
- **Don't hardcode technology choices in Design agent prompts.**
  The agent evaluates and chooses — that's the whole point.
- **Don't default to React/PostgreSQL/AWS.** Read what the
  documents suggest. A government project might need Java/SQL
  Server/Azure GovCloud.
- **Don't build features for FAANG customers we don't have.**
  Build for consulting firms we're trying to close.
- **Don't add agent #9.** We have 8. Ship all 8 before adding more.
- **Don't skip multi-tenancy thinking.** Every new table needs
  tenant_id. Every new query needs tenant filtering.
- **Don't commit .env files.**
- **Don't put business logic in route handlers.**
- **Don't make skills stateful or database-aware.**
- **Don't skip few-shot examples in task prompts.**