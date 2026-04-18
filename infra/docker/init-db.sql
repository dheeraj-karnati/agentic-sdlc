-- Agentic SDLC Platform - Database Initialization
-- Runs automatically on first PostgreSQL start

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ─── Enum Types ───
CREATE TYPE project_status AS ENUM (
  'created', 'ingest', 'discover', 'design', 'prototype',
  'plan', 'build', 'test', 'ship', 'completed'
);

CREATE TYPE agent_type AS ENUM (
  'ingest', 'discover', 'design', 'prototype',
  'plan', 'build', 'test', 'ship'
);

CREATE TYPE run_status AS ENUM (
  'pending', 'running', 'paused_for_input',
  'paused_for_approval', 'completed', 'failed'
);

CREATE TYPE approval_status AS ENUM (
  'pending', 'approved', 'rejected', 'revision_requested'
);

CREATE TYPE artifact_type AS ENUM (
  'document', 'schema', 'api_spec', 'code',
  'diagram', 'plan', 'prototype', 'config'
);

CREATE TYPE message_direction AS ENUM (
  'agent_to_user', 'user_to_agent'
);

-- ─── Core Tables ───
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  status project_status NOT NULL DEFAULT 'created',
  config JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_type agent_type NOT NULL,
  status run_status NOT NULL DEFAULT 'pending',
  input_context JSONB DEFAULT '{}',
  output_summary JSONB DEFAULT '{}',
  error_details TEXT,
  token_usage JSONB DEFAULT '{}',
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
  type artifact_type NOT NULL,
  name VARCHAR(500) NOT NULL,
  s3_key VARCHAR(1000),
  content TEXT,
  version INTEGER DEFAULT 1,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE approval_gates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  status approval_status NOT NULL DEFAULT 'pending',
  reviewer_notes TEXT,
  decided_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
  direction message_direction NOT NULL,
  message TEXT NOT NULL,
  structured_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE business_context (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_agent agent_type,
  category VARCHAR(100) NOT NULL,
  title VARCHAR(500),
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Planning Tables ───
CREATE TYPE epic_status AS ENUM ('draft', 'approved', 'in_progress', 'done');
CREATE TYPE story_status AS ENUM ('draft', 'approved', 'in_progress', 'done');

CREATE TABLE epics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
  title VARCHAR(500) NOT NULL,
  description TEXT,
  priority INTEGER NOT NULL DEFAULT 0,
  sequence_order INTEGER NOT NULL DEFAULT 0,
  status epic_status NOT NULL DEFAULT 'draft',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_stories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  epic_id UUID NOT NULL REFERENCES epics(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title VARCHAR(500) NOT NULL,
  description TEXT,
  acceptance_criteria JSONB DEFAULT '[]',
  story_points INTEGER,
  priority INTEGER NOT NULL DEFAULT 0,
  sequence_order INTEGER NOT NULL DEFAULT 0,
  status story_status NOT NULL DEFAULT 'draft',
  technical_notes TEXT,
  schema_changes TEXT,
  api_endpoints JSONB DEFAULT '[]',
  ui_components JSONB DEFAULT '[]',
  dependencies JSONB DEFAULT '[]',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE error_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  environment VARCHAR(50) NOT NULL,
  severity VARCHAR(20) NOT NULL DEFAULT 'error',
  stack_trace TEXT,
  root_cause_analysis TEXT,
  suggested_fix TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'new',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Indexes ───
CREATE INDEX idx_agent_runs_project ON agent_runs(project_id);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_artifacts_project ON artifacts(project_id);
CREATE INDEX idx_artifacts_type ON artifacts(type);
CREATE INDEX idx_conversations_project ON conversations(project_id);
CREATE INDEX idx_business_context_project ON business_context(project_id);
CREATE INDEX idx_business_context_category ON business_context(category);
CREATE INDEX idx_error_reports_project ON error_reports(project_id);
CREATE INDEX idx_error_reports_status ON error_reports(status);

CREATE INDEX idx_epics_project ON epics(project_id);
CREATE INDEX idx_epics_sequence ON epics(project_id, sequence_order);
CREATE INDEX idx_user_stories_epic ON user_stories(epic_id);
CREATE INDEX idx_user_stories_project ON user_stories(project_id);
CREATE INDEX idx_user_stories_sequence ON user_stories(epic_id, sequence_order);

-- pgvector HNSW index for fast similarity search
CREATE INDEX idx_business_context_embedding
  ON business_context USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
