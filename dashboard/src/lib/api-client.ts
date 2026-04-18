import axios from "axios";
import type { AgentStatusResponse, AgentType, ApprovalGate, ApprovalStatus, Artifact, Project, UploadResult } from "./types";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

/* ── Projects ── */

export async function listProjects(): Promise<{ projects: Project[]; total: number }> {
  const { data } = await api.get("/api/projects/");
  return data;
}

export async function getProject(id: string): Promise<Project> {
  const { data } = await api.get(`/api/projects/${id}`);
  return data;
}

export async function createProject(name: string, description?: string): Promise<Project> {
  const { data } = await api.post("/api/projects/", { name, description });
  return data;
}

/* ── File Upload ── */

export async function uploadFiles(projectId: string, files: File[]): Promise<UploadResult> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const { data } = await api.post(`/api/projects/${projectId}/ingest/upload`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300_000,
  });
  return data;
}

export async function importUrl(projectId: string, url: string): Promise<UploadResult> {
  const { data } = await api.post(`/api/projects/${projectId}/ingest/import`, { urls: [{ url }], s3_keys: [] });
  return data;
}

/* ── Agents ── */

const AGENT_START_PATHS: Partial<Record<AgentType, string>> = {
  ingest: "agents/ingest/start",
  discover: "agents/discovery/start",
  design: "agents/design/start",
  prototype: "agents/prototype/start",
};

export async function startAgent(projectId: string, agentType: AgentType, payload?: Record<string, unknown>): Promise<{ run_id: string }> {
  const path = AGENT_START_PATHS[agentType];
  if (!path) throw new Error(`Agent ${agentType} cannot be started yet`);
  const { data } = await api.post(`/api/projects/${projectId}/${path}`, payload ?? {});
  return data;
}

export async function getLatestRun(projectId: string): Promise<AgentRunSummary | null> {
  try {
    const { data } = await api.get(`/api/projects/${projectId}/agents/latest`);
    return data;
  } catch {
    return null;
  }
}

export async function getAgentStatus(projectId: string, runId: string): Promise<AgentStatusResponse> {
  const { data } = await api.get(`/api/projects/${projectId}/agents/${runId}/status`);
  return data;
}

export async function respondToAgent(projectId: string, runId: string, answers: { question: string; answer: string }[]): Promise<void> {
  await api.post(`/api/projects/${projectId}/agents/${runId}/respond`, { answers });
}

/* ── Approvals ── */

export async function listApprovals(projectId: string): Promise<{ approvals: ApprovalGate[]; total: number }> {
  const { data } = await api.get(`/api/projects/${projectId}/approvals/`);
  return data;
}

export async function decideApproval(projectId: string, gateId: string, status: ApprovalStatus, notes?: string): Promise<Record<string, unknown>> {
  const { data } = await api.post(`/api/projects/${projectId}/approvals/${gateId}/decide`, { status, reviewer_notes: notes });
  return data;
}

/* ── Runs ── */

export interface AgentRunSummary {
  id: string;
  run_id?: string;  // alias returned by /agents/latest
  agent_type: AgentType;
  status: string;
  output_summary: Record<string, unknown>;
  error_details: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  approval_gate?: { id: string; status: string; reviewer_notes: string | null } | null;
}

export async function listRuns(projectId: string): Promise<AgentRunSummary[]> {
  const { data } = await api.get(`/api/projects/${projectId}/runs`);
  return data;
}

/* ── Artifacts ── */

export async function listArtifacts(projectId: string): Promise<Artifact[]> {
  const { data } = await api.get(`/api/projects/${projectId}/artifacts`);
  return Array.isArray(data) ? data : data.artifacts ?? [];
}
