"use client";

import { useState, useEffect, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useProject } from "@/lib/hooks/use-project";
import { useApprovals } from "@/lib/hooks/use-approvals";
import { useStartAgent } from "@/lib/hooks/use-agent";
import { PipelineBar } from "@/components/dashboard/pipeline-bar";
import { AgentDetailPanel } from "@/components/dashboard/agent-detail-panel";
import { ActivitySidebar } from "@/components/dashboard/activity-sidebar";
import { AGENTS, STATUS_TO_AGENT } from "@/lib/types";
import type { AgentType, AgentStatusResponse } from "@/lib/types";
import { getAgentStatus, getLatestRun } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";

function ProjectContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.id as string;
  const runIdFromUrl = searchParams.get("runId");

  const { data: project, isLoading } = useProject(projectId);
  const startAgentMut = useStartAgent();

  // "viewingAgent" = which agent's report the user is LOOKING at (changes on pipeline click)
  // This is separate from which agent is actively running.
  const [viewingAgent, setViewingAgent] = useState<AgentType | null>(null);

  // ─── Always track the LATEST run (for polling) ───
  const { data: latestRun } = useQuery({
    queryKey: ["latest-run", projectId],
    queryFn: () => getLatestRun(projectId),
    enabled: !!projectId,
    refetchInterval: 30000,
  });

  const activeRunId = latestRun?.run_id ?? latestRun?.id ?? runIdFromUrl ?? undefined;

  // Poll the active/latest run status
  const { data: agentStatusFromActive } = useQuery<AgentStatusResponse | null>({
    queryKey: ["agent-status-poll", projectId, activeRunId],
    queryFn: () => (activeRunId ? getAgentStatus(projectId, activeRunId) : Promise.resolve(null)),
    enabled: !!projectId && !!activeRunId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "running" || status === "pending") return 30000;
      return false;
    },
  });

  // ─── Fetch ALL runs for this project (to view completed agents) ───
  const { data: allRuns } = useQuery({
    queryKey: ["all-runs", projectId],
    queryFn: async () => {
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/projects/${projectId}/runs`);
      return resp.ok ? resp.json() : [];
    },
    enabled: !!projectId,
    refetchInterval: 30000,
  });

  // Find the run for the agent the user is VIEWING
  const viewingRun = viewingAgent
    ? (allRuns as any[])?.find((r: any) => r.agent_type === viewingAgent && r.status !== "pending")
    : undefined;

  // Fetch status for the viewed agent's run (if different from active)
  const viewingRunId = viewingRun?.id;
  const isViewingActive = !viewingAgent || viewingAgent === (agentStatusFromActive?.agent_type as AgentType);

  const { data: viewedAgentStatus } = useQuery<AgentStatusResponse | null>({
    queryKey: ["agent-status-viewed", projectId, viewingRunId],
    queryFn: () => (viewingRunId ? getAgentStatus(projectId, viewingRunId) : Promise.resolve(null)),
    enabled: !!viewingRunId && !isViewingActive,
  });

  // The status to DISPLAY: either the active run or the viewed historical run
  const displayedStatus = isViewingActive ? agentStatusFromActive : viewedAgentStatus;

  // Approvals
  const currentAgentStatus = agentStatusFromActive?.status;
  const { data: approvalsData } = useApprovals(projectId, currentAgentStatus);
  const approvals = approvalsData?.approvals ?? [];
  const pendingGateFromList = approvals.find((g) => g.status === "pending");
  const embeddedGate = (agentStatusFromActive as any)?.approval_gate;
  const pendingGate = pendingGateFromList ?? (
    embeddedGate && embeddedGate.status === "pending"
      ? { id: embeddedGate.id, project_id: projectId, agent_run_id: activeRunId ?? "", status: "pending" as const, reviewer_notes: null, decided_at: null, created_at: "" }
      : undefined
  );

  // Auto-follow the active agent (unless user clicked a different stage)
  useEffect(() => {
    if (agentStatusFromActive?.agent_type) {
      setViewingAgent(agentStatusFromActive.agent_type);
    } else if (project) {
      const current = STATUS_TO_AGENT[project.status];
      if (current) setViewingAgent(current);
    }
  }, [project, agentStatusFromActive]);

  const handleStageClick = (agentType: AgentType) => {
    setViewingAgent(agentType);
  };

  // When clicking "back to current" — return to active agent
  const handleBackToCurrent = () => {
    if (agentStatusFromActive?.agent_type) {
      setViewingAgent(agentStatusFromActive.agent_type);
    }
  };

  const currentPhaseAgent = project ? STATUS_TO_AGENT[project.status] : null;
  const selectedAgent = viewingAgent;
  const agentMeta = AGENTS.find((a) => a.id === selectedAgent);
  const canStart = selectedAgent === currentPhaseAgent && !activeRunId && !agentStatusFromActive;

  const handleStart = () => {
    if (!selectedAgent || !agentMeta?.available) return;
    if (selectedAgent === "discover") {
      startAgentMut.mutate({ projectId, agentType: "discover", payload: { document_text: "See ingested sources" } });
    } else {
      startAgentMut.mutate({ projectId, agentType: selectedAgent });
    }
  };

  if (isLoading || !project) {
    return <div className="flex items-center justify-center h-[60vh]"><Loader2 className="w-6 h-6 animate-spin text-d8x-text-tertiary" /></div>;
  }

  // Show "viewing history" banner if looking at a completed agent while another is active
  const isViewingHistory = !isViewingActive && displayedStatus && (agentStatusFromActive?.status === "running" || agentStatusFromActive?.status === "pending");

  return (
    <div className="flex flex-col h-[calc(100vh-56px)]">
      <PipelineBar projectStatus={project.status} activeRunStatus={agentStatusFromActive?.status as any} onStageClick={handleStageClick} />

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-[65] overflow-y-auto p-6">
          {/* Banner: viewing historical agent while another is running */}
          {isViewingHistory && (
            <div className="mb-4 flex items-center justify-between px-4 py-2.5 bg-d8x-blue/10 border border-d8x-blue/20 rounded-lg">
              <span className="text-xs text-d8x-blue">
                Viewing completed {agentMeta?.label} report. {AGENTS.find(a => a.id === agentStatusFromActive?.agent_type)?.label} is still running in the background.
              </span>
              <button onClick={handleBackToCurrent} className="text-xs text-d8x-blue font-medium hover:underline">
                Back to {AGENTS.find(a => a.id === agentStatusFromActive?.agent_type)?.label} →
              </button>
            </div>
          )}

          {/* Start agent prompt */}
          {canStart && agentMeta?.available && (
            <div className="mb-6 bg-d8x-surface border border-d8x-gold/20 rounded-lg p-6 text-center">
              <h3 className="text-lg font-semibold mb-2">{agentMeta.num}: {agentMeta.label} is ready</h3>
              <p className="text-sm text-d8x-text-secondary mb-4">Click below to start the {agentMeta.label} agent.</p>
              <Button onClick={handleStart} disabled={startAgentMut.isPending} className="bg-d8x-gold text-d8x-background hover:bg-d8x-gold-light">
                {startAgentMut.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                Start {agentMeta.label}
              </Button>
            </div>
          )}

          {selectedAgent && !agentMeta?.available && (
            <div className="flex items-center justify-center h-40 text-d8x-text-secondary text-sm">{agentMeta?.num}: {agentMeta?.label} — coming soon</div>
          )}

          {/* Show the displayed agent's report (either active or historical) */}
          {displayedStatus && (
            <AgentDetailPanel
              projectId={projectId}
              agentStatus={displayedStatus}
              pendingGate={isViewingActive ? pendingGate : undefined}
            />
          )}

          {!displayedStatus && activeRunId && isViewingActive && (
            <div className="flex items-center justify-center h-40 gap-2 text-d8x-text-secondary text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Loading agent status...</div>
          )}

          {!displayedStatus && !activeRunId && !canStart && selectedAgent && agentMeta?.available && (
            <div className="flex items-center justify-center h-40 text-d8x-text-secondary text-sm">Complete previous stages first to reach {agentMeta.label}.</div>
          )}
        </div>

        <div className="flex-[35] max-w-sm">
          <ActivitySidebar project={project} approvals={approvals} />
        </div>
      </div>
    </div>
  );
}

export default function ProjectDetailPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-[60vh]"><Loader2 className="w-6 h-6 animate-spin text-d8x-text-tertiary" /></div>}>
      <ProjectContent />
    </Suspense>
  );
}
