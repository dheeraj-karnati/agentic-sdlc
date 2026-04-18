-- D8X Enum Migration: old D8 names → new clear names
-- Run this against an existing database to migrate without data loss.
--
-- Usage: psql -h <host> -U sdlc -d agentic_sdlc -f scripts/migrate_enums.sql

BEGIN;

-- ═══════════════════════════════════════════
-- 1. Migrate project_status enum
-- ═══════════════════════════════════════════

CREATE TYPE project_status_new AS ENUM (
  'created', 'ingest', 'discover', 'design', 'prototype',
  'plan', 'build', 'test', 'ship', 'completed'
);

-- Map old values to new values via a text cast + case expression
ALTER TABLE projects
  ALTER COLUMN status TYPE project_status_new
  USING (
    CASE status::text
      WHEN 'created'        THEN 'created'
      WHEN 'digitize'       THEN 'ingest'
      WHEN 'discovery'      THEN 'discover'
      WHEN 'design'         THEN 'design'
      WHEN 'demo'           THEN 'prototype'
      WHEN 'prototype'      THEN 'prototype'
      WHEN 'define'         THEN 'plan'
      WHEN 'planning'       THEN 'plan'
      WHEN 'develop'        THEN 'build'
      WHEN 'implementation' THEN 'build'
      WHEN 'detect'         THEN 'test'
      WHEN 'deployment'     THEN 'ship'
      WHEN 'completed'      THEN 'completed'
      ELSE 'created'
    END
  )::project_status_new;

DROP TYPE project_status;
ALTER TYPE project_status_new RENAME TO project_status;

-- ═══════════════════════════════════════════
-- 2. Migrate agent_type enum
-- ═══════════════════════════════════════════

CREATE TYPE agent_type_new AS ENUM (
  'ingest', 'discover', 'design', 'prototype',
  'plan', 'build', 'test', 'ship'
);

-- agent_runs.agent_type
ALTER TABLE agent_runs
  ALTER COLUMN agent_type TYPE agent_type_new
  USING (
    CASE agent_type::text
      WHEN 'digitize'       THEN 'ingest'
      WHEN 'discovery'      THEN 'discover'
      WHEN 'design'         THEN 'design'
      WHEN 'demo'           THEN 'prototype'
      WHEN 'prototype'      THEN 'prototype'
      WHEN 'define'         THEN 'plan'
      WHEN 'planning'       THEN 'plan'
      WHEN 'develop'        THEN 'build'
      WHEN 'implementation' THEN 'build'
      WHEN 'detect'         THEN 'test'
      WHEN 'deploy'         THEN 'ship'
      WHEN 'deployment'     THEN 'ship'
      ELSE 'ingest'
    END
  )::agent_type_new;

-- business_context.source_agent
ALTER TABLE business_context
  ALTER COLUMN source_agent TYPE agent_type_new
  USING (
    CASE source_agent::text
      WHEN 'digitize'       THEN 'ingest'
      WHEN 'discovery'      THEN 'discover'
      WHEN 'design'         THEN 'design'
      WHEN 'demo'           THEN 'prototype'
      WHEN 'prototype'      THEN 'prototype'
      WHEN 'define'         THEN 'plan'
      WHEN 'planning'       THEN 'plan'
      WHEN 'develop'        THEN 'build'
      WHEN 'implementation' THEN 'build'
      WHEN 'detect'         THEN 'test'
      WHEN 'deploy'         THEN 'ship'
      WHEN 'deployment'     THEN 'ship'
      ELSE NULL
    END
  )::agent_type_new;

DROP TYPE agent_type;
ALTER TYPE agent_type_new RENAME TO agent_type;

-- ═══════════════════════════════════════════
-- 3. Update business_context categories
-- ═══════════════════════════════════════════

UPDATE business_context
SET category = 'ingested_source'
WHERE category = 'digitized_source';

COMMIT;

-- Verify
SELECT enumlabel FROM pg_enum
JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
WHERE pg_type.typname = 'agent_type'
ORDER BY enumsortorder;

SELECT enumlabel FROM pg_enum
JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
WHERE pg_type.typname = 'project_status'
ORDER BY enumsortorder;
