import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAgentStatus, respondToAgent, startAgent } from "../api-client";
import type { AgentType, RunStatus } from "../types";

const POLLING_STATUSES: RunStatus[] = ["pending", "running"];

export function useAgentStatus(projectId: string, runId: string | undefined) {
  return useQuery({
    queryKey: ["agent-status", projectId, runId],
    queryFn: () => getAgentStatus(projectId, runId!),
    enabled: !!projectId && !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && POLLING_STATUSES.includes(status)) return 2000;
      if (status === "paused_for_input" || status === "paused_for_approval") return 10000;
      return false;
    },
  });
}

export function useStartAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { projectId: string; agentType: AgentType; payload?: Record<string, unknown> }) =>
      startAgent(vars.projectId, vars.agentType, vars.payload),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["project", vars.projectId] });
    },
  });
}

export function useRespondToAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { projectId: string; runId: string; answers: { question: string; answer: string }[] }) =>
      respondToAgent(vars.projectId, vars.runId, vars.answers),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["agent-status", vars.projectId, vars.runId] });
    },
  });
}
