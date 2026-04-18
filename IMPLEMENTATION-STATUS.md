# Agentic SDLC — Implementation Status & Workflow

## Current Workflow (What's Implemented)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                        │
│                                                                    │
│  docker-compose.yml starts:                                        │
│  ┌──────────┐  ┌───────┐  ┌───────┐  ┌──────┐  ┌─────────┐       │
│  │PostgreSQL │  │ Redis │  │ MinIO │  │ Loki │  │ Grafana │       │
│  │+ pgvector│  │  7    │  │  S3   │  │ logs │  │ monitor │       │
│  │  pg16    │  │       │  │       │  │      │  │         │       │
│  └────┬─────┘  └───────┘  └───────┘  └──────┘  └─────────┘       │
│       │                                                            │
│  init-db.sql runs on first boot:                                   │
│  → Creates pgvector + pg_trgm extensions                           │
│  → Creates 8 enum types (incl. epic_status, story_status)          │
│  → Creates 9 tables (projects, agent_runs, artifacts,              │
│    approval_gates, conversations, business_context, error_reports, │
│    epics, user_stories)                                            │
│  → Creates 14 indexes including HNSW vector index                  │
└───────┼─────────────────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────────────┐
│                       CONFIGURATION LAYER                           │
│                                                                     │
│  .env  ──loads──▶  config.py (Settings)                             │
│                    Pydantic BaseSettings singleton                   │
│                    Fields: database_url, redis_url, s3_*,           │
│                    anthropic_api_key, github_token, langsmith        │
│                           │                                         │
│                    Used by every module via:                         │
│                    from src.config import settings                   │
└───────────────────┼─────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────────┐
│                      DATABASE / ORM LAYER                           │
│                                                                     │
│  database.py                      models.py                         │
│  ┌─────────────────────┐          ┌──────────────────────────┐      │
│  │ create_async_engine  │          │ Base (DeclarativeBase)   │      │
│  │ async_session_factory│          │ 8 Enums (ProjectStatus,  │      │
│  │ get_db() dependency  │──uses──▶│   AgentType, RunStatus,  │      │
│  │  (yield session,     │          │   EpicStatus, Story…)    │      │
│  │   commit/rollback)   │          │ 9 Models (Project,       │      │
│  └─────────────────────┘          │   AgentRun, Artifact,    │      │
│                                    │   ApprovalGate, Epic,    │      │
│                                    │   UserStory, Conversation│      │
│                                    │   BusinessContext w/     │      │
│                                    │   Vector(1536),          │      │
│                                    │   ErrorReport)           │      │
│                                    └──────────┬───────────────┘      │
│                                               │                     │
│  repository.py                                │                     │
│  ┌────────────────────────────────────────────┘                     │
│  │ BusinessContextRepository(session)                               │
│  │  ├─ store_context()      → INSERT + flush + refresh              │
│  │  ├─ search_similar()     → cosine_distance ORDER BY + LIMIT      │
│  │  ├─ get_by_category()    → WHERE project_id + category           │
│  │  └─ get_all_for_project()→ WHERE project_id                      │
│  └──────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────────┐
│                         TOOLS LAYER                                 │
│                                                                     │
│  tools/embeddings.py                                                │
│  ┌──────────────────────────────────────────────┐                   │
│  │ embed_text()       → async, returns 1536-dim vector              │
│  │ embed_texts()      → batch embedding                             │
│  │ chunk_text()       → token-based chunking (tiktoken cl100k_base) │
│  │ _average_vectors() → vector averaging for multi-chunk embeddings │
│  │ Model: text-embedding-3-small (OpenAI)                           │
│  └──────────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                         │
│                                                                     │
│  main.py                                                            │
│  ┌──────────────────────────────────────────────┐                   │
│  │ FastAPI app                                   │                  │
│  │ ├─ CORS middleware (localhost:3000)            │                 │
│  │ ├─ GET /health → HealthResponse               │                   │
│  │ └─ includes routers: projects, agents,        │                   │
│  │    approvals, planning at /api                │                   │
│  └──────────────────┬───────────────────────────┘                   │
│                     │                                               │
│  routes/projects.py │    schemas/project.py                         │
│  ┌──────────────────▼──┐  ┌──────────────────────────┐              │
│  │ POST   /api/projects│  │ ProjectCreate/Update/     │              │
│  │ GET    /api/projects│  │   Response/ListResponse   │              │
│  │ GET    /api/projects│  │ AgentRunCreate/Response   │              │
│  │        /{id}        │◀─│ ApprovalDecision/Response │              │
│  │ PATCH  /api/projects│  │ ConversationMsg schemas   │              │
│  │        /{id}        │  │ Discovery schemas:        │              │
│  │ DELETE /api/projects│  │   Start, Clarification,   │              │
│  │        /{id}        │  │   UserAnswer, Respond     │              │
│  └─────────────────────┘  │ Design schemas:           │              │
│                            │   Start, Artifact,        │              │
│  routes/agents.py          │   DesignOutput            │              │
│  ┌─────────────────────┐  │ Prototype schemas:        │              │
│  │ Discovery Agent:    │  │   Start, Output,          │              │
│  │  POST .../discovery/│  │   Feedback, FeedbackResp  │              │
│  │       start         │  │ HealthResponse            │              │
│  │  GET  .../{run_id}/ │  └──────────────────────────┘              │
│  │       status        │                                            │
│  │  POST .../{run_id}/ │  routes/approvals.py                       │
│  │       respond       │  ┌─────────────────────────┐              │
│  │  POST .../{run_id}/ │  │ GET  .../approvals/      │              │
│  │       skip-questions│  │ GET  .../approvals/      │              │
│  │ Design Agent:       │  │      {gate_id}           │              │
│  │  POST .../design/   │  │ POST .../approvals/      │              │
│  │       start         │  │      {gate_id}/decide    │              │
│  │  GET  .../{run_id}/ │  │ Handles: approved,       │              │
│  │       design-output │  │  rejected, revision_     │              │
│  │ Prototype Agent:    │  │  requested + re-trigger  │              │
│  │  POST .../prototype/│  │  (discovery, design,     │              │
│  │       start         │  │   prototype, planning)   │              │
│  │  GET  .../{run_id}/ │  └─────────────────────────┘              │
│  │    prototype-output │                                            │
│  │  POST .../{run_id}/ │  routes/planning.py                        │
│  │       feedback      │  ┌─────────────────────────┐              │
│  └─────────────────────┘  │ POST .../planning/start  │              │
│                            │ GET  .../planning/       │              │
│                            │      {run_id}/output     │              │
│                            │ GET  .../planning/epics  │              │
│                            │ PUT  .../planning/epics/ │              │
│                            │      {epic_id}           │              │
│                            │ GET  .../planning/stories│              │
│                            │ POST .../planning/stories│              │
│                            │ PUT  .../planning/stories│              │
│                            │      /{story_id}         │              │
│                            │ DELETE .../planning/     │              │
│                            │      stories/{story_id}  │              │
│                            │ POST .../planning/stories│              │
│                            │      /resequence         │              │
│                            └─────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────────┐
│                    AGENT LAYER (LangGraph)                          │
│                                                                     │
│  agents/discovery/agent.py (FULLY IMPLEMENTED)                      │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ DiscoveryState (TypedDict)                            │           │
│  │   project_id, document_text, findings, is_clear,      │           │
│  │   questions, user_responses, stored_count, errors     │           │
│  │                                                       │           │
│  │ StateGraph:                                           │           │
│  │   START ──▶ parse_documents ──▶ check_clarity         │           │
│  │                                      │                │           │
│  │              ┌───────────────────────┘                │           │
│  │              ├─ has_questions → END (interrupt)        │           │
│  │              └─ clear → store_findings → END          │           │
│  │                                                       │           │
│  │ Features: dependency injection, user response          │           │
│  │   injection for resumption, skip_clarity flag,        │           │
│  │   auto-computes embeddings, error handling             │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                     │
│  agents/design/agent.py (FULLY IMPLEMENTED)                         │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ DesignState (TypedDict)                               │           │
│  │   project_id, agent_run_id, reviewer_notes,           │           │
│  │   business_context, design, artifacts_stored, errors  │           │
│  │                                                       │           │
│  │ StateGraph:                                           │           │
│  │   START ──▶ load_context ──▶ generate_design          │           │
│  │                  ──▶ store_artifacts ──▶ END           │           │
│  │                                                       │           │
│  │ Generates 5 design sections:                          │           │
│  │   1. Architecture (components, communication)         │           │
│  │   2. Database Schema (DDL, tables, relationships)     │           │
│  │   3. API Specification (endpoints, auth)              │           │
│  │   4. Authentication Design (JWT/OAuth2, roles)        │           │
│  │   5. Frontend Components (hierarchy, state, routing)  │           │
│  │                                                       │           │
│  │ Features: reviewer_notes for revisions, stores each   │           │
│  │   section as separate Artifact record                 │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                     │
│  agents/prototype/agent.py (FULLY IMPLEMENTED)                      │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ PrototypeState (TypedDict)                            │           │
│  │   project_id, agent_run_id, reviewer_notes,           │           │
│  │   design_artifacts, previous_prototype,               │           │
│  │   feedback_history, prototype, artifacts_stored,      │           │
│  │   artifact_version, errors                            │           │
│  │                                                       │           │
│  │ StateGraph:                                           │           │
│  │   START ──▶ load_design ──▶ generate_prototype        │           │
│  │                  ──▶ store_prototype ──▶ END           │           │
│  │                                                       │           │
│  │ Generates self-contained Next.js/React prototype:     │           │
│  │   - page_code (full React component w/ Tailwind CSS)  │           │
│  │   - mock_data (realistic data matching DB schema)     │           │
│  │   - component_manifest (components + workflows)       │           │
│  │   - setup_instructions                                │           │
│  │                                                       │           │
│  │ Features:                                             │           │
│  │   - Loads design artifacts from DB (not context store)│           │
│  │   - Cumulative feedback loop: previous_prototype +    │           │
│  │     feedback_history injected for iterative refinement │           │
│  │   - Versioned artifacts (incremented per iteration)   │           │
│  │   - reviewer_notes for approval revisions             │           │
│  │   - Feedback stored as Conversation records           │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                     │
│  agents/planning/agent.py (FULLY IMPLEMENTED)                       │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ PlanningState (TypedDict)                            │           │
│  │   project_id, agent_run_id, reviewer_notes,          │           │
│  │   design_artifacts, prototype_artifacts,              │           │
│  │   business_context, epics, stories,                   │           │
│  │   validation_issues, epics_stored, stories_stored     │           │
│  │                                                       │           │
│  │ StateGraph (7 nodes):                                │           │
│  │   START ──▶ gather_context ──▶ generate_epics         │           │
│  │     ──▶ generate_stories ──▶ sequence_stories         │           │
│  │     ──▶ validate_plan ──▶ store_plan                  │           │
│  │     ──▶ create_approval ──▶ END                       │           │
│  │                                                       │           │
│  │ Features:                                             │           │
│  │   - Gathers design + prototype + business context     │           │
│  │   - Generates epics with priority and sequence        │           │
│  │   - Generates stories per epic with acceptance        │           │
│  │     criteria, story points, technical notes,          │           │
│  │     schema changes, API endpoints, UI components,     │           │
│  │     and dependencies (JSONB arrays)                   │           │
│  │   - Topological sort by dependencies                  │           │
│  │   - Validates plan completeness                       │           │
│  │   - Stores Epic + UserStory records in DB             │           │
│  │   - Stores plan summary as Artifact                   │           │
│  │   - reviewer_notes for approval revisions             │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                     │
│  agents/implementation/ → EMPTY (only __init__.py)                  │
│  agents/deployment/  → EMPTY (only __init__.py)                     │
└─────────────────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────────┐
│                    ORCHESTRATOR LAYER                               │
│                                                                     │
│  orchestrator/pipeline.py (PARTIAL)                                 │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ WorkflowState (TypedDict)                             │           │
│  │   project_id, current_phase, phase_status,            │           │
│  │   pending_questions, approval_decision, phase_outputs │           │
│  │                                                       │           │
│  │ create_initial_state() factory function               │           │
│  │                                                       │           │
│  │ Phase nodes (stubs): discovery_node, design_node,     │           │
│  │   prototype_node, planning_node                       │           │
│  │                                                       │           │
│  │ StateGraph:                                           │           │
│  │   discovery → approval_discovery                      │           │
│  │     ├─ approved → design → approval_design            │           │
│  │     │               ├─ approved → prototype           │           │
│  │     │               │    → approval_prototype         │           │
│  │     │               │       ├─ approved → planning    │           │
│  │     │               │       │    → approval_planning  │           │
│  │     │               │       │       ├─ approved → END │           │
│  │     │               │       │       ├─ retry → plan.  │           │
│  │     │               │       │       └─ rejected → END │           │
│  │     │               │       ├─ retry → prototype      │           │
│  │     │               │       └─ rejected → END         │           │
│  │     │               ├─ retry → design                 │           │
│  │     │               └─ rejected → END                 │           │
│  │     ├─ retry → discovery                              │           │
│  │     └─ rejected → END                                 │           │
│  │                                                       │           │
│  │ Note: Stub nodes; agents run via API routes           │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                     │
│  orchestrator/approval.py (FULLY IMPLEMENTED)                       │
│  ┌──────────────────────────────────────────────────────┐           │
│  │ PHASE_TRANSITIONS mapping (AgentType → ProjectStatus) │           │
│  │ PHASE_STATUS mapping                                  │           │
│  │ create_approval_gate() → creates pending gate +       │           │
│  │   transitions run to PAUSED_FOR_APPROVAL              │           │
│  │ process_decision() → handles approved/rejected/       │           │
│  │   revision_requested with full state transitions      │           │
│  └──────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────────────┐
│                    TESTING & VERIFICATION                           │
│                                                                     │
│  tests/unit/ (13 test files, ~4,000+ lines)                        │
│  ┌─────────────────────────────┬──────────────────────────────┐    │
│  │ test_projects.py            │ Health check + CRUD basics    │    │
│  │ test_context_store.py       │ Repository CRUD + similarity  │    │
│  │ test_embeddings.py          │ Embedding funcs + chunking    │    │
│  │ test_discovery_agent.py     │ Graph nodes, routing, errors  │    │
│  │ test_design_agent.py        │ Graph nodes, error scenarios  │    │
│  │ test_agent_routes.py        │ Discovery/Design endpoints    │    │
│  │ test_design_routes.py       │ Design endpoint specifics     │    │
│  │ test_approval_logic.py      │ Gate creation + decisions     │    │
│  │ test_approval_routes.py     │ Approval endpoints + retrigger│    │
│  │ test_prototype_agent.py     │ Graph nodes, feedback loop,   │    │
│  │                             │   versioning, format helpers  │    │
│  │ test_prototype_routes.py    │ Start/output/feedback endpts, │    │
│  │                             │   cumulative history, guards  │    │
│  │ test_planning_agent.py     │ 24 tests: 7 graph nodes,      │    │
│  │                             │   sequencing, validation,     │    │
│  │                             │   storage, error paths        │    │
│  │ test_planning_routes.py    │ 9 tests: start, epic CRUD,    │    │
│  │                             │   story CRUD, resequence,     │    │
│  │                             │   guards (status, 404)        │    │
│  └─────────────────────────────┴──────────────────────────────┘    │
│                                                                     │
│  scripts/                                                           │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │ verify-setup.sh       → Environment validation (bash)   │       │
│  │ smoke_test.py         → API/DB/Redis connectivity test  │       │
│  │ test_discovery.py     → E2E discovery flow test         │       │
│  │ test_design_flow.py   → E2E design flow test            │       │
│  │ test_full_flow.py     → Full pipeline E2E test          │       │
│  └─────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Working End-to-End Flow

```
1. POST /api/projects/                          → Create project
2. POST /api/projects/{id}/agents/discovery/start
   → Creates AgentRun (PENDING)
   → Launches discovery graph async:
     parse_documents → check_clarity → [conditional]
       ├─ has_questions → status = PAUSED_FOR_INPUT (awaits user)
       └─ clear → store_findings to business_context → COMPLETED
   → Auto-creates ApprovalGate

3. POST .../agents/{run_id}/respond             → Submit answers to questions
   OR POST .../agents/{run_id}/skip-questions   → Skip clarification
   → Re-runs graph with injected responses

4. POST /api/projects/{id}/approvals/{gate_id}/decide
   ├─ APPROVED    → Project advances to DESIGN phase
   ├─ REJECTED    → AgentRun marked failed
   └─ REVISION_REQUESTED → New AgentRun with reviewer notes, re-triggers agent

5. POST /api/projects/{id}/agents/design/start
   → Launches design graph async:
     load_context → generate_design → store_artifacts → COMPLETED
   → Generates 5 design sections as Artifact records
   → Auto-creates ApprovalGate

6. POST /api/projects/{id}/approvals/{gate_id}/decide
   → Same approval flow as step 4
   → On APPROVED: Project advances to PROTOTYPE phase

7. POST /api/projects/{id}/agents/prototype/start
   → Launches prototype graph async:
     load_design → generate_prototype → store_prototype → COMPLETED
   → Generates self-contained React/Next.js prototype with mock data
   → Stores 4 artifacts (page_code, mock_data, component_manifest,
     setup_instructions) as ArtifactType.PROTOTYPE
   → Auto-creates ApprovalGate

8. POST /api/projects/{id}/agents/{run_id}/feedback
   → Feedback loop (can be called multiple times):
     a. Stores feedback as Conversation (direction: user_to_agent)
     b. Gathers ALL prior prototype feedback for cumulative history
     c. Creates new AgentRun with incremented version
     d. Re-runs prototype graph with:
        - Original design artifacts (loaded fresh from DB)
        - Previous prototype output (for cumulative improvement)
        - Full feedback history (numbered, oldest to newest)
     e. Stores new versioned artifacts
     f. Auto-creates new ApprovalGate

9. POST /api/projects/{id}/approvals/{gate_id}/decide
   → Same approval flow as step 4
   → On APPROVED: Project advances to PLANNING phase
   → On REVISION_REQUESTED: Re-triggers prototype agent with
     reviewer notes

10. POST /api/projects/{id}/planning/start
    → Launches planning graph async (7 nodes):
      gather_context → generate_epics → generate_stories
        → sequence_stories → validate_plan → store_plan
        → create_approval → COMPLETED
    → Gathers design artifacts, prototype artifacts, business context
    → Generates epics with priorities and sequence ordering
    → Generates user stories per epic with acceptance criteria,
      story points, technical notes, schema changes, API endpoints,
      UI components, and dependencies
    → Topologically sorts stories by dependencies
    → Validates plan completeness (all epics have stories,
      all dependency references valid)
    → Stores Epic + UserStory records in DB
    → Stores plan summary as Artifact (ArtifactType.PLAN)
    → Auto-creates ApprovalGate

11. Planning CRUD (PO can edit before approval):
    GET  .../planning/epics              → List all epics
    PUT  .../planning/epics/{epic_id}    → Update epic fields
    GET  .../planning/stories            → List stories (filter by epic)
    POST .../planning/stories            → Add new story
    PUT  .../planning/stories/{id}       → Update story fields
    DELETE .../planning/stories/{id}     → Delete story (cascades deps)
    POST .../planning/stories/resequence → Reorder stories

12. POST /api/projects/{id}/approvals/{gate_id}/decide
    → Same approval flow as step 4
    → On APPROVED: Project advances to IMPLEMENTATION phase
      (implementation/deployment agents not yet implemented)
    → On REVISION_REQUESTED: Re-triggers planning agent with
      reviewer notes
```

---

## File-by-File Functionality

### Configuration

| File | What It Does |
|------|-------------|
| **`pyproject.toml`** | Defines project metadata, 19 core dependencies (LangChain, FastAPI, SQLAlchemy, pgvector, boto3, redis…), 5 dev dependencies (pytest, ruff, mypy), and tool configs (ruff rules, pytest asyncio_mode=auto, mypy strict) |
| **`.env.example`** | Template for all env vars: Anthropic key, DB URLs (async+sync), Redis, MinIO creds, GitHub token, LangSmith tracing. Warns not to export ANTHROPIC_API_KEY in shell |
| **`src/config.py`** | `Settings` class (pydantic-settings) loads `.env` into typed fields. Exports a `settings` singleton used by every module |

### Infrastructure

| File | What It Does |
|------|-------------|
| **`infra/docker/docker-compose.yml`** | Starts 5 services: PostgreSQL 16 + pgvector (port 5432), Redis 7 (6379), MinIO (9000/9001), Loki (3100), Grafana (3001). All with health checks and named volumes |
| **`infra/docker/init-db.sql`** | First-boot SQL: enables `vector` + `pg_trgm` extensions, creates 8 enum types (incl. epic_status, story_status), 9 tables (incl. epics, user_stories) with UUID PKs/TIMESTAMPTZ/JSONB/Vector(1536) columns, 14 indexes including HNSW vector index for cosine similarity |

### Database / ORM

| File | What It Does |
|------|-------------|
| **`src/context_store/database.py`** | Creates async SQLAlchemy engine (asyncpg driver, pool_size=5). Exports `get_db()` — a FastAPI dependency that yields a session, auto-commits on success, rolls back on exception |
| **`src/context_store/models.py`** | Defines 8 enums (`ProjectStatus`, `AgentType`, `RunStatus`, `ApprovalStatus`, `ArtifactType`, `MessageDirection`, `EpicStatus`, `StoryStatus`) and 9 ORM models (`Project`, `AgentRun`, `Artifact`, `ApprovalGate`, `Conversation`, `BusinessContext` with Vector(1536), `Epic`, `UserStory`, `ErrorReport`). `Epic` has title/description/priority/sequence_order/status. `UserStory` has acceptance_criteria (JSONB), story_points, technical_notes, schema_changes, api_endpoints/ui_components/dependencies (JSONB arrays). All use UUID PKs, JSONB, and `values_callable` for correct enum serialization |
| **`src/context_store/repository.py`** | `BusinessContextRepository` — takes an AsyncSession, provides `store_context()` (insert + flush + refresh), `search_similar()` (pgvector cosine distance ordering), `get_by_category()`, and `get_all_for_project()` |

### Tools

| File | What It Does |
|------|-------------|
| **`src/tools/embeddings.py`** | OpenAI text-embedding-3-small integration: `embed_text()` (async, 1536-dim vectors), `embed_texts()` (batch), `chunk_text()` (token-based chunking with tiktoken cl100k_base, max 8000 tokens), `_average_vectors()` for multi-chunk embeddings |

### API

| File | What It Does |
|------|-------------|
| **`src/api/main.py`** | Creates the FastAPI app with CORS (allows localhost:3000), mounts routers for projects, agents, approvals, and planning at `/api`, and exposes `GET /health` returning `{status, version, environment}` |
| **`src/api/routes/projects.py`** | 5 CRUD endpoints: `POST /api/projects/` (create, 201), `GET /api/projects/` (list with skip/limit pagination), `GET /{id}` (get or 404), `PATCH /{id}` (partial update via `exclude_unset`), `DELETE /{id}` (204 or 404). All use `Depends(get_db)` for sessions |
| **`src/api/routes/agents.py`** | Discovery endpoints: `POST .../discovery/start`, `GET .../{run_id}/status`, `POST .../{run_id}/respond`, `POST .../{run_id}/skip-questions`. Design endpoints: `POST .../design/start`, `GET .../{run_id}/design-output`. Prototype endpoints: `POST .../prototype/start`, `GET .../{run_id}/prototype-output`, `POST .../{run_id}/feedback` (feedback loop with cumulative history, versioned artifacts, conversation storage). Background task functions handle graph execution, status updates, and auto-create approval gates on completion |
| **`src/api/routes/approvals.py`** | 3 endpoints: `GET .../approvals/` (list), `GET .../approvals/{gate_id}` (detail with agent run info), `POST .../approvals/{gate_id}/decide` (submit decision). On APPROVED: transitions project to next phase. On REVISION_REQUESTED: creates new AgentRun with reviewer_notes and re-triggers the agent (supports discovery, design, prototype, and planning agents) |
| **`src/api/routes/planning.py`** | Planning CRUD routes: `POST .../planning/start` (launch planning agent), `GET .../planning/{run_id}/output` (get epics + stories), `GET /epics` (list), `PUT /epics/{id}` (update), `GET /stories` (list, filter by epic), `POST /stories` (create with auto-sequence), `PUT /stories/{id}` (update), `DELETE /stories/{id}` (cascade dependency removal), `POST /stories/resequence` (batch reorder). Background task runs planning graph and auto-creates approval gate |
| **`src/api/schemas/project.py`** | Pydantic v2 models: Project CRUD schemas, AgentRun schemas, Approval schemas, Conversation schemas, Discovery schemas (Start, Clarification, UserAnswer, Respond), Design schemas (Start, Artifact, DesignOutput), Prototype schemas (Start, Output, Feedback, FeedbackResponse with version), Planning schemas (Start, EpicResponse/Update, UserStoryResponse/Create/Update, ResequenceRequest/Item, PlanningOutput), HealthResponse |

### Agents

| File | What It Does |
|------|-------------|
| **`src/agents/discovery/agent.py`** | Full LangGraph StateGraph: `parse_documents` (Claude extracts business_rules/requirements/technical_details as JSON) → `check_clarity` (reviews for ambiguity, generates questions) → conditional routing (has_questions → END/interrupt, clear → `store_findings` with embeddings → END). Supports dependency injection, user response injection, skip_clarity flag |
| **`src/agents/design/agent.py`** | Full LangGraph StateGraph: `load_context` (fetches business_context from discovery) → `generate_design` (Claude generates 5 sections: architecture, database, API, auth, frontend) → `store_artifacts` (saves each section as Artifact record). Supports reviewer_notes for revision reruns |
| **`src/agents/prototype/agent.py`** | Full LangGraph StateGraph: `load_design` (queries design artifacts from DB) → `generate_prototype` (Claude generates self-contained Next.js page with React components, Tailwind CSS, mock data) → `store_prototype` (saves 4 versioned artifacts as ArtifactType.PROTOTYPE). Supports cumulative feedback loop: `previous_prototype` + `feedback_history` are injected into LLM context so iterations build on prior work. Versioned artifacts with `artifact_version` from state. Reviewer_notes for approval revisions |
| **`src/agents/planning/agent.py`** | Full LangGraph StateGraph (7 nodes): `gather_context` (loads design + prototype artifacts + business context) → `generate_epics` (Claude generates prioritized epics) → `generate_stories` (Claude generates stories per epic with acceptance criteria, story points, technical notes, schema changes, API endpoints, UI components, dependencies) → `sequence_stories` (topological sort by dependencies) → `validate_plan` (checks completeness: all epics have stories, all deps valid) → `store_plan` (writes Epic + UserStory records) → `create_approval` (stores plan summary artifact). Supports reviewer_notes for revision reruns |
| **`src/agents/implementation/`** | Empty — only `__init__.py` |
| **`src/agents/deployment/`** | Empty — only `__init__.py` |

### Orchestrator

| File | What It Does |
|------|-------------|
| **`src/orchestrator/pipeline.py`** | `WorkflowState` TypedDict + `create_initial_state()` factory. `build_pipeline()` creates a LangGraph StateGraph with stub nodes for discovery, design, prototype, and planning, each followed by approval gates with conditional routing (approved → next phase, retry → same phase, rejected → END). Prototype approval routes to planning; planning approval routes to END (TODO: implementation). Stub nodes only — agents currently run via API routes |
| **`src/orchestrator/approval.py`** | `PHASE_TRANSITIONS` and `PHASE_STATUS` mappings (all 6 agent types). `create_approval_gate()` creates pending gate + transitions run to PAUSED_FOR_APPROVAL. `process_decision()` handles approved/rejected/revision_requested with full Project/AgentRun/Gate state transitions |

### Tests & Scripts

| File | What It Does |
|------|-------------|
| **`tests/unit/test_projects.py`** | Health check + basic project CRUD tests |
| **`tests/unit/test_context_store.py`** | 8 tests covering all 4 repository methods with AsyncMock sessions |
| **`tests/unit/test_embeddings.py`** | Comprehensive tests for embed_text, embed_texts, chunk_text functions |
| **`tests/unit/test_discovery_agent.py`** | Tests all discovery graph nodes (parse, clarity, store), conditional routing, error handling |
| **`tests/unit/test_design_agent.py`** | Tests all design graph nodes (load, generate, store), error scenarios |
| **`tests/unit/test_agent_routes.py`** | Tests discovery/design API endpoints, background task execution, status checks |
| **`tests/unit/test_design_routes.py`** | Tests design-specific endpoint behavior |
| **`tests/unit/test_approval_logic.py`** | Tests approval gate creation, decision processing, phase transitions |
| **`tests/unit/test_approval_routes.py`** | Tests approval endpoints, revision re-trigger logic |
| **`tests/unit/test_prototype_agent.py`** | 26 tests: graph nodes (load_design, generate, store), feedback loop (previous prototype injection, cumulative feedback history, combined context), versioned artifacts, format helpers, full graph execution, error paths |
| **`tests/unit/test_prototype_routes.py`** | 13 tests: start endpoint (success, wrong status, reviewer notes, 404), output endpoint (success, 404, errors), feedback endpoint (creates conversation + new run, accumulates history, rejects non-prototype runs, rejects wrong status, rejects empty feedback, passes previous prototype) |
| **`scripts/verify-setup.sh`** | Checks CLI tools, Docker services, pgvector extension, DB tables, .venv, packages, .env vars |
| **`scripts/smoke_test.py`** | Async integration: Anthropic API, DB connectivity, pgvector search, Redis |
| **`scripts/test_discovery.py`** | E2E test for the discovery agent flow |
| **`scripts/test_design_flow.py`** | E2E test for the design agent flow |
| **`scripts/test_full_flow.py`** | E2E test for the full discovery → design pipeline |

---

## Overall Progress

| Component | Status | Complete | Notes |
|-----------|--------|----------|-------|
| **Infrastructure** | Done | 100% | Docker Compose with 5 services, all running |
| **Database Schema** | Done | 100% | 9 tables (incl. epics, user_stories), 8 enums, 14 indexes, HNSW vector index, pgvector |
| **Configuration** | Done | 100% | pydantic-settings, .env, pyproject.toml |
| **ORM Models** | Done | 100% | 9 models (incl. Epic, UserStory) with relationships, 8 enums |
| **API Schemas** | Done | 100% | All Pydantic v2 models: Discovery + Design + Prototype (incl. Feedback) + Planning (Epic/Story CRUD, Resequence) |
| **Project CRUD API** | Done | 100% | 5 endpoints + health check |
| **Agent Routes API** | Done | 100% | Discovery (start/status/respond/skip) + Design (start/output) + Prototype (start/output/feedback) + Planning (start/output + epic/story CRUD + resequence) |
| **Approval Routes API** | Done | 100% | List/get/decide endpoints with revision re-trigger for discovery, design, prototype, planning |
| **Context Store Repo** | Done | 90% | BusinessContext repo done; other repos missing |
| **Tools / Embeddings** | Done | 100% | OpenAI embed, batch embed, chunking with tiktoken |
| **Discovery Agent** | Done | 100% | Full LangGraph: parse → clarity → store, with HITL interrupt |
| **Design Agent** | Done | 100% | Full LangGraph: load context → generate → store artifacts |
| **Prototype Agent** | Done | 100% | Full LangGraph: load design → generate prototype → store. Feedback loop with cumulative history, versioned artifacts, conversation storage |
| **Approval Logic** | Done | 100% | Gate creation, decision processing, phase transitions |
| **Planning Agent** | Done | 100% | Full LangGraph (7 nodes): gather_context → generate_epics → generate_stories → sequence_stories → validate_plan → store_plan → create_approval. Stores Epic + UserStory records. Topological dependency sorting. Separate CRUD routes for PO editing |
| **Orchestrator Pipeline** | Partial | ~55% | 4 phase nodes (discovery/design/prototype/planning) with approval gates chained; stub nodes only |
| **Implementation Agent** | Empty | 0% | Only `__init__.py` |
| **Deployment Agent** | Empty | 0% | Only `__init__.py` |
| **Dashboard** | Empty | 0% | Directory exists, no code |
| **CI/CD** | Empty | 0% | No GitHub Actions workflows |
| **Unit Tests** | Done | ~95% | 13 test files, ~4,000+ lines covering all implemented agents (discovery, design, prototype, planning), routes, approvals, tools |
| **Integration/E2E Tests** | Partial | ~30% | E2E scripts exist in scripts/ but no automated test framework |