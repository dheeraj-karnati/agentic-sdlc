"use client";

import type { AgentStatusResponse, ApprovalGate } from "@/lib/types";
import { AGENTS } from "@/lib/types";
import { Loader2, CheckCircle2, AlertTriangle, XCircle, Eye } from "lucide-react";
import { MetricCard } from "./metric-card";
import { StatusBadge } from "./status-badge";
import { IngestReport } from "./ingest-report";
import { DiscoverReport } from "./discover-report";
import { DesignReport } from "./design-report";
import { ApprovalActions } from "./approval-actions";
import { ReportDownload } from "./report-download";
import { ImproveAnalysis } from "./improve-analysis";

/* eslint-disable @typescript-eslint/no-explicit-any */

interface AgentDetailPanelProps {
  projectId: string;
  agentStatus?: AgentStatusResponse;
  pendingGate?: ApprovalGate;
}

export function AgentDetailPanel({ projectId, agentStatus, pendingGate }: AgentDetailPanelProps) {
  if (!agentStatus) {
    return <div className="flex items-center justify-center h-64 text-d8x-text-secondary text-sm">Select a pipeline stage or start an agent to see details.</div>;
  }

  const agent = AGENTS.find((a) => a.id === agentStatus.agent_type);
  const agentLabel = agent ? `${agent.num}: ${agent.label}` : agentStatus.agent_type;
  const output = agentStatus.output_summary as Record<string, any> ?? {};
  const tasks = (output.tasks ?? []) as any[];
  const metrics = output.metrics ?? {};
  const isReview = agentStatus.status === "paused_for_approval";
  const isRunning = agentStatus.status === "running" || agentStatus.status === "pending";
  const isCompleted = agentStatus.status === "completed";

  // Use gate from props, or extract from agentStatus response
  const embeddedGate = (agentStatus as any).approval_gate;
  const resolvedGate = pendingGate ?? (
    embeddedGate && embeddedGate.status === "pending"
      ? { id: embeddedGate.id, project_id: projectId, agent_run_id: String(agentStatus.run_id), status: "pending" as const, reviewer_notes: null, decided_at: null, created_at: "" }
      : undefined
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isRunning && <Loader2 className="w-5 h-5 text-d8x-gold animate-spin" />}
          {isCompleted && <CheckCircle2 className="w-5 h-5 text-d8x-success" />}
          {isReview && <Eye className="w-5 h-5 text-d8x-warning" />}
          {agentStatus.status === "paused_for_input" && <AlertTriangle className="w-5 h-5 text-d8x-warning" />}
          {agentStatus.status === "failed" && <XCircle className="w-5 h-5 text-d8x-danger" />}
          <h2 className="text-lg font-bold">{agentLabel}</h2>
          <StatusBadge status={agentStatus.status} />
        </div>
        <div className="flex items-center gap-3">
          {agentStatus.started_at && (
            <span className="text-xs text-d8x-text-secondary">Started {new Date(agentStatus.started_at).toLocaleTimeString()}</span>
          )}
          {(isReview || isCompleted) && (
            <ReportDownload projectId={projectId} agentType={agentStatus.agent_type} />
          )}
        </div>
      </div>

      {/* ── RUNNING STATE: Metrics + task progress ── */}
      {isRunning && (
        <>
          {Object.keys(metrics).length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {getMetricCards(agentStatus.agent_type, metrics).map(([label, value]) => (
                <MetricCard key={label} label={label} value={value} />
              ))}
            </div>
          )}
          {tasks.length > 0 ? (
            <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5 space-y-3">
              {tasks.map((task: any) => (
                <div key={task.name} className="flex items-start gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${
                    task.status === "completed" ? "bg-d8x-success" : task.status === "running" ? "bg-d8x-blue animate-pulse" : task.status === "failed" ? "bg-d8x-danger" : "bg-d8x-text-tertiary"
                  }`} />
                  <div>
                    <p className="text-sm font-medium">{task.label}</p>
                    <p className="text-xs text-d8x-text-secondary">{task.detail || (task.status === "pending" ? "Waiting" : "")}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
              <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-d8x-gold animate-pulse" /><span className="text-sm">Agent is working...</span></div>
            </div>
          )}
        </>
      )}

      {/* ── REVIEW / COMPLETED STATE: Beautiful report + approval ── */}
      {(isReview || isCompleted) && (
        <>
          {agentStatus.agent_type === "ingest" && <IngestReport output={output} />}
          {agentStatus.agent_type === "discover" && <DiscoverReport output={output} />}
          {agentStatus.agent_type === "design" && <DesignReport output={output} />}
          {!["ingest", "discover", "design"].includes(agentStatus.agent_type) && Object.keys(output).length > 0 && (
            <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
              <h3 className="text-sm font-semibold mb-3">Output</h3>
              <pre className="text-xs bg-d8x-background rounded p-3 overflow-auto max-h-[400px] font-mono whitespace-pre-wrap">{JSON.stringify(output, null, 2)}</pre>
            </div>
          )}
          {/* Improve analysis — only for ingest, before approval buttons */}
          {agentStatus.agent_type === "ingest" && isReview && (
            <ImproveAnalysis
              projectId={projectId}
              currentMetrics={{
                quality_score: Number(metrics.quality_score ?? 0),
                completeness: Number(output.quality_assessment?.completeness ?? 0),
                diversity: Number(output.quality_assessment?.diversity ?? 0),
                volume: Number(output.quality_assessment?.volume ?? 0),
              }}
              currentFileCount={Number(metrics.files_processed ?? 0)}
            />
          )}

          {resolvedGate && resolvedGate.status === "pending" && (
            <ApprovalActions projectId={projectId} gateId={resolvedGate.id} agentType={agentStatus.agent_type} />
          )}
        </>
      )}

      {/* ── FAILED STATE ── */}
      {agentStatus.status === "failed" && (
        <div className="bg-d8x-danger/10 border border-d8x-danger/20 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-d8x-danger mb-2">Agent failed</h3>
          {agentStatus.errors.map((e, i) => <p key={i} className="text-sm text-d8x-danger/80">{e}</p>)}
        </div>
      )}
    </div>
  );
}

function getMetricCards(agentType: string, metrics: Record<string, any>): [string, string | number][] {
  switch (agentType) {
    case "ingest":
      return [["Files processed", metrics.files_processed ?? 0], ["Words extracted", (metrics.words_extracted ?? 0).toLocaleString()], ["Sources classified", metrics.sources_classified ?? 0], ["Quality score", metrics.quality_score ? `${metrics.quality_score}/100` : "—"]];
    case "discover":
      return [["Rules found", metrics.rules_found ?? 0], ["Entities", metrics.entities ?? 0], ["Conflicts", metrics.conflicts ?? 0], ["Quality score", metrics.quality_score ? `${metrics.quality_score}/100` : "—"]];
    case "design":
      return [["Tables", metrics.tables ?? 0], ["Endpoints", metrics.endpoints ?? 0], ["Components", metrics.components ?? 0], ["Quality score", metrics.quality_score ? `${metrics.quality_score}/100` : "—"]];
    case "prototype":
      return [["Pages", metrics.pages ?? 0], ["Components", metrics.components ?? 0], ["Files", metrics.files ?? 0], ["Quality score", metrics.quality_score ? `${metrics.quality_score}/100` : "—"]];
    default:
      return Object.entries(metrics).slice(0, 4).map(([k, v]) => [k.replace(/_/g, " "), String(v)]);
  }
}
