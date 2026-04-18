# Agentic SDLC — Architecture Diagrams for Presentation

> Render each Mermaid block at https://mermaid.live — export as PNG/SVG and paste into PowerPoint.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph CLIENT["Frontend (Planned)"]
        DASH["Next.js Dashboard<br/><i>React + Tailwind + shadcn/ui</i>"]
    end

    subgraph API["API Layer — FastAPI"]
        HEALTH["GET /health"]
        PROJ["Projects API<br/><i>CRUD endpoints</i>"]
        AGENT["Agents API<br/><i>Discovery / Design / Prototype / Planning</i>"]
        APPR["Approvals API<br/><i>HITL decision gates</i>"]
    end

    subgraph AGENTS["Agent Layer — LangGraph"]
        A1["Discovery Agent<br/><i>Parse docs → Extract findings</i>"]
        A2["Design Agent<br/><i>Generate system design</i>"]
        A3["Prototype Agent<br/><i>Generate React prototype</i>"]
        A4["Planning Agent<br/><i>Epics → Stories → Sequence</i>"]
        A5["Implementation Agent<br/><i>Planned</i>"]
        A6["Deployment Agent<br/><i>Planned</i>"]
    end

    subgraph ORCHESTRATOR["Orchestrator"]
        PIPE["Pipeline<br/><i>LangGraph state machine</i>"]
        GATE["Approval Logic<br/><i>Phase transitions</i>"]
    end

    subgraph INFRA["Infrastructure"]
        PG["PostgreSQL 16<br/>+ pgvector"]
        REDIS["Redis 7<br/><i>Streams</i>"]
        MINIO["MinIO<br/><i>S3 storage</i>"]
        MON["Grafana + Loki<br/><i>Monitoring</i>"]
    end

    subgraph AI["AI Services"]
        CLAUDE["Claude API<br/><i>Anthropic</i>"]
        EMBED["OpenAI Embeddings<br/><i>text-embedding-3-small</i>"]
    end

    DASH -->|REST| API
    AGENT --> AGENTS
    AGENTS --> ORCHESTRATOR
    AGENTS -->|LLM calls| CLAUDE
    A1 -->|embed findings| EMBED
    ORCHESTRATOR --> GATE
    AGENTS -->|read/write| PG
    GATE -->|update state| PG

    style CLIENT fill:#f0f0f0,stroke:#999,stroke-dasharray: 5 5
    style A5 fill:#f0f0f0,stroke:#999,stroke-dasharray: 5 5
    style A6 fill:#f0f0f0,stroke:#999,stroke-dasharray: 5 5
```

---

## 2. SDLC Pipeline Flow (End-to-End)

```mermaid
flowchart LR
    START(("Start")) --> DISC

    subgraph DISC["Phase 1: Discovery"]
        D1["Parse Legacy<br/>Documents"] --> D2["Check Clarity"]
        D2 -->|unclear| D3["Ask User<br/>Questions"]
        D3 -->|answers| D2
        D2 -->|clear| D4["Store Findings<br/>+ Embeddings"]
    end

    DISC --> G1{{"Approval<br/>Gate"}}
    G1 -->|Approved| DESIGN

    subgraph DESIGN["Phase 2: Design"]
        E1["Load Business<br/>Context"] --> E2["Generate<br/>System Design"]
        E2 --> E3["Store 5 Design<br/>Artifacts"]
    end

    DESIGN --> G2{{"Approval<br/>Gate"}}
    G2 -->|Approved| PROTO

    subgraph PROTO["Phase 3: Prototype"]
        F1["Load Design<br/>Artifacts"] --> F2["Generate React<br/>Prototype"]
        F2 --> F3["Store Versioned<br/>Artifacts"]
    end

    F3 -.->|User Feedback| F2

    PROTO --> G3{{"Approval<br/>Gate"}}
    G3 -->|Approved| PLAN

    subgraph PLAN["Phase 4: Planning"]
        PL1["Gather Context<br/><i>Design + Prototype + Biz</i>"] --> PL2["Generate<br/>Epics"]
        PL2 --> PL3["Generate Stories<br/><i>per Epic</i>"]
        PL3 --> PL4["Sequence &<br/>Validate"]
        PL4 --> PL5["Store Plan<br/><i>Epics + Stories</i>"]
    end

    PL5 -.->|PO Edits CRUD| PL5

    PLAN --> G4{{"Approval<br/>Gate"}}
    G4 -->|Approved| FUTURE

    subgraph FUTURE["Phase 5–6"]
        F1["Implementation<br/><i>Planned</i>"]
        F2["Deployment<br/><i>Planned</i>"]
    end

    G1 -->|"Revision"| DISC
    G2 -->|"Revision"| DESIGN
    G3 -->|"Revision"| PROTO
    G4 -->|"Revision"| PLAN

    style FUTURE fill:#f0f0f0,stroke:#999,stroke-dasharray: 5 5
    style F1 fill:#f0f0f0,stroke:#999,stroke-dasharray: 5 5
    style F2 fill:#f0f0f0,stroke:#999,stroke-dasharray: 5 5
```

---

## 3. Prototype Agent — Feedback Loop Detail

```mermaid
flowchart TD
    START(("Design<br/>Approved")) --> LOAD["load_design<br/><i>Fetch design artifacts<br/>from DB</i>"]
    LOAD --> GEN["generate_prototype<br/><i>Claude generates React page<br/>+ mock data + manifest</i>"]
    GEN --> STORE["store_prototype<br/><i>Save 4 artifacts<br/>(version N)</i>"]
    STORE --> GATE{{"Approval Gate<br/><i>PAUSED_FOR_APPROVAL</i>"}}

    GATE -->|"User submits feedback"| FB["POST /{run_id}/feedback"]
    FB --> CONV["Store as Conversation<br/><i>user_to_agent</i>"]
    CONV --> HIST["Gather cumulative<br/>feedback history"]
    HIST --> NEWRUN["Create new AgentRun<br/><i>version N+1</i>"]
    NEWRUN --> LOAD2["load_design<br/><i>Same design artifacts</i>"]
    LOAD2 --> GEN2["generate_prototype<br/><i>Injected context:</i><br/>Previous prototype<br/>+ All feedback history"]
    GEN2 --> STORE2["store_prototype<br/><i>Save 4 artifacts<br/>(version N+1)</i>"]
    STORE2 --> GATE

    GATE -->|Approved| NEXT(("Next Phase"))
    GATE -->|Revision| REV["Re-trigger with<br/>reviewer notes"]
    REV --> LOAD
```

---

## 4. Planning Agent — 7-Node Pipeline Detail

```mermaid
flowchart TD
    START(("Prototype<br/>Approved")) --> GC["gather_context<br/><i>Load design artifacts<br/>+ prototype + biz context</i>"]
    GC --> GE["generate_epics<br/><i>Claude generates 4–8<br/>prioritised epics</i>"]
    GE --> GS["generate_stories<br/><i>Claude generates stories<br/>per epic with AC, points,<br/>tech notes, deps</i>"]
    GS --> SS["sequence_stories<br/><i>Topological sort<br/>by dependencies</i>"]
    SS --> VP["validate_plan<br/><i>Check: all epics have stories,<br/>all deps valid</i>"]
    VP --> SP["store_plan<br/><i>Write Epic + UserStory<br/>records to DB</i>"]
    SP --> CA["create_approval<br/><i>Store plan artifact<br/>+ approval gate</i>"]
    CA --> GATE{{"Approval Gate<br/><i>PAUSED_FOR_APPROVAL</i>"}}

    GATE -->|"PO edits via CRUD"| CRUD["Epic/Story CRUD<br/><i>PUT/POST/DELETE/resequence</i>"]
    CRUD --> GATE

    GATE -->|Approved| NEXT(("Next Phase"))
    GATE -->|Revision| REV["Re-trigger with<br/>reviewer notes"]
    REV --> GC
```

---

## 5. Data Model (Entity Relationship)

```mermaid
erDiagram
    PROJECTS ||--o{ AGENT_RUNS : has
    PROJECTS ||--o{ ARTIFACTS : produces
    PROJECTS ||--o{ APPROVAL_GATES : requires
    PROJECTS ||--o{ CONVERSATIONS : tracks
    PROJECTS ||--o{ BUSINESS_CONTEXT : stores
    PROJECTS ||--o{ EPICS : plans
    PROJECTS ||--o{ USER_STORIES : breaks_down
    PROJECTS ||--o{ ERROR_REPORTS : logs

    AGENT_RUNS ||--o{ ARTIFACTS : generates
    AGENT_RUNS ||--o{ APPROVAL_GATES : triggers
    AGENT_RUNS ||--o{ CONVERSATIONS : contains
    AGENT_RUNS ||--o{ EPICS : produces

    EPICS ||--o{ USER_STORIES : contains

    PROJECTS {
        uuid id PK
        string name
        string description
        enum status "created|discovery|design|prototype|planning|implementation|deployment|completed"
        jsonb config
    }

    AGENT_RUNS {
        uuid id PK
        uuid project_id FK
        enum agent_type "discovery|design|prototype|planning|implementation|deployment"
        enum status "pending|running|paused_for_input|paused_for_approval|completed|failed"
        jsonb input_context
        jsonb output_summary
    }

    ARTIFACTS {
        uuid id PK
        uuid project_id FK
        uuid agent_run_id FK
        enum type "document|schema|api_spec|code|diagram|plan|prototype|config"
        string name
        text content
        int version
        jsonb metadata
    }

    APPROVAL_GATES {
        uuid id PK
        uuid project_id FK
        uuid agent_run_id FK
        enum status "pending|approved|rejected|revision_requested"
        text reviewer_notes
        timestamp decided_at
    }

    BUSINESS_CONTEXT {
        uuid id PK
        uuid project_id FK
        enum source_agent
        string category
        text content
        vector embedding "1536-dim"
    }

    EPICS {
        uuid id PK
        uuid project_id FK
        uuid agent_run_id FK
        string title
        text description
        int priority
        int sequence_order
        enum status "draft|approved|in_progress|done"
        jsonb metadata
    }

    USER_STORIES {
        uuid id PK
        uuid epic_id FK
        uuid project_id FK
        string title
        text description
        jsonb acceptance_criteria
        int story_points
        int priority
        int sequence_order
        enum status "draft|approved|in_progress|done"
        text technical_notes
        text schema_changes
        jsonb api_endpoints
        jsonb ui_components
        jsonb dependencies
    }

    CONVERSATIONS {
        uuid id PK
        uuid project_id FK
        uuid agent_run_id FK
        enum direction "agent_to_user|user_to_agent"
        text message
        jsonb structured_data
    }
```

---

## 6. API Endpoints Map

```mermaid
graph LR
    subgraph HEALTH["Health"]
        H1["GET /health"]
    end

    subgraph PROJECTS["Projects — /api/projects"]
        P1["POST /"]
        P2["GET /"]
        P3["GET /{id}"]
        P4["PATCH /{id}"]
        P5["DELETE /{id}"]
    end

    subgraph DISCOVERY["Discovery Agent"]
        D1["POST /{id}/agents/discovery/start"]
        D2["GET /{id}/agents/{run}/status"]
        D3["POST /{id}/agents/{run}/respond"]
        D4["POST /{id}/agents/{run}/skip-questions"]
    end

    subgraph DESIGNAPI["Design Agent"]
        E1["POST /{id}/agents/design/start"]
        E2["GET /{id}/agents/{run}/design-output"]
    end

    subgraph PROTOAPI["Prototype Agent"]
        F1["POST /{id}/agents/prototype/start"]
        F2["GET /{id}/agents/{run}/prototype-output"]
        F3["POST /{id}/agents/{run}/feedback"]
    end

    subgraph PLANAPI["Planning Agent"]
        PL1["POST /{id}/planning/start"]
        PL2["GET /{id}/planning/{run}/output"]
        PL3["GET /{id}/planning/epics"]
        PL4["PUT /{id}/planning/epics/{epic}"]
        PL5["GET/POST /{id}/planning/stories"]
        PL6["PUT/DELETE /{id}/planning/stories/{s}"]
        PL7["POST /{id}/planning/stories/resequence"]
    end

    subgraph APPROVALS["Approvals"]
        A1["GET /{id}/approvals/"]
        A2["GET /{id}/approvals/{gate}"]
        A3["POST /{id}/approvals/{gate}/decide"]
    end
```

---

## 7. Tech Stack Overview

```mermaid
block-beta
    columns 4

    block:FRONTEND:1
        columns 1
        FH["Frontend"]
        F1["Next.js 14+"]
        F2["TypeScript"]
        F3["Tailwind CSS"]
        F4["shadcn/ui"]
    end

    block:BACKEND:1
        columns 1
        BH["Backend"]
        B1["Python 3.12+"]
        B2["FastAPI"]
        B3["SQLAlchemy 2.0"]
        B4["Pydantic v2"]
    end

    block:AIML:1
        columns 1
        AH["AI / ML"]
        A1["LangChain"]
        A2["LangGraph"]
        A3["Claude API"]
        A4["OpenAI Embeddings"]
    end

    block:INFRA2:1
        columns 1
        IH["Infrastructure"]
        I1["PostgreSQL + pgvector"]
        I2["Redis Streams"]
        I3["MinIO (S3)"]
        I4["Grafana + Loki"]
    end

    style FH fill:#3b82f6,color:#fff
    style BH fill:#10b981,color:#fff
    style AH fill:#8b5cf6,color:#fff
    style IH fill:#f59e0b,color:#fff
```

---

## 8. Implementation Progress

```mermaid
pie title Implementation Progress by Component
    "Completed" : 14
    "Partial" : 2
    "Not Started" : 4
```

| Status | Components |
|--------|-----------|
| **Completed (14)** | Infrastructure, DB Schema, Config, ORM Models, API Schemas, Project CRUD, Agent Routes, Approval Routes, Planning Routes, Context Store, Embeddings, Discovery Agent, Design Agent, Prototype Agent, Planning Agent |
| **Partial (2)** | Orchestrator Pipeline (~55%), Integration/E2E Tests (~30%) |
| **Not Started (4)** | Implementation Agent, Deployment Agent, Dashboard, CI/CD |

---

## How to Use

1. Go to **https://mermaid.live**
2. Paste any code block above (between the ` ```mermaid ` markers)
3. Click **Actions → Export PNG** (or SVG for crisp scaling)
4. Insert the image into your PowerPoint slide
5. Adjust background to match your slide theme

> Tip: For dark-themed slides, use Mermaid's `%%{init: {'theme': 'dark'}}%%` at the top of any diagram.