/* D8X TypeScript types — mirrors backend Pydantic schemas */

export type ProjectStatus = 'created' | 'ingest' | 'discover' | 'design' | 'prototype' | 'plan' | 'build' | 'test' | 'ship' | 'completed';
export type AgentType = 'ingest' | 'discover' | 'design' | 'prototype' | 'plan' | 'build' | 'test' | 'ship';
export type RunStatus = 'pending' | 'running' | 'paused_for_input' | 'paused_for_approval' | 'completed' | 'failed';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'revision_requested';
export type ArtifactType = 'document' | 'schema' | 'api_spec' | 'code' | 'diagram' | 'plan' | 'prototype' | 'config';

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ClarificationQuestion {
  finding_title: string;
  question: string;
  reason: string;
}

export interface AgentStatusResponse {
  run_id: string;
  agent_type: AgentType;
  status: RunStatus;
  pending_questions: ClarificationQuestion[];
  output_summary: Record<string, unknown>;
  errors: string[];
  started_at: string | null;
  completed_at: string | null;
}

export interface ApprovalGate {
  id: string;
  project_id: string;
  agent_run_id: string;
  status: ApprovalStatus;
  reviewer_notes: string | null;
  decided_at: string | null;
  created_at: string;
  agent_type?: AgentType;
  run_status?: RunStatus;
  output_summary?: Record<string, unknown>;
}

export interface Artifact {
  id: string;
  project_id: string;
  agent_run_id: string | null;
  type: ArtifactType;
  name: string;
  content: string | null;
  version: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface UploadResult {
  resolved_files: { s3_key: string; original_filename: string; content_type: string; size_bytes: number; source_type: string }[];
  total_files: number;
  total_bytes: number;
  errors: string[];
}

/* ── Agent display metadata ── */
export const AGENTS: { id: AgentType; label: string; num: string; available: boolean }[] = [
  { id: 'ingest', label: 'Ingest', num: 'D1', available: true },
  { id: 'discover', label: 'Discover', num: 'D2', available: true },
  { id: 'design', label: 'Design', num: 'D3', available: true },
  { id: 'prototype', label: 'Prototype', num: 'D4', available: true },
  { id: 'plan', label: 'Plan', num: 'D5', available: false },
  { id: 'build', label: 'Build', num: 'D6', available: false },
  { id: 'test', label: 'Test', num: 'D7', available: false },
  { id: 'ship', label: 'Ship', num: 'D8', available: false },
];

/* Map project status → which agent is current */
export const STATUS_TO_AGENT: Record<ProjectStatus, AgentType | null> = {
  created: null, ingest: 'ingest', discover: 'discover', design: 'design',
  prototype: 'prototype', plan: 'plan', build: 'build', test: 'test',
  ship: 'ship', completed: null,
};

/* Map project status → which agents are completed */
export function getCompletedAgents(status: ProjectStatus): AgentType[] {
  const order: AgentType[] = ['ingest', 'discover', 'design', 'prototype', 'plan', 'build', 'test', 'ship'];
  const idx = order.indexOf(STATUS_TO_AGENT[status] ?? 'ingest');
  return idx > 0 ? order.slice(0, idx) : [];
}
