import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { decideApproval, listApprovals } from "../api-client";
import type { ApprovalStatus } from "../types";

export function useApprovals(projectId: string, agentStatus?: string) {
  return useQuery({
    queryKey: ["approvals", projectId],
    queryFn: () => listApprovals(projectId),
    enabled: !!projectId,
    // Only poll while agent is running (waiting for gate to be created).
    // Stop polling once we have a paused_for_approval status or completed.
    refetchInterval: agentStatus === "running" || agentStatus === "pending" ? 30000 : false,
  });
}

export function useDecideApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { projectId: string; gateId: string; status: ApprovalStatus; notes?: string }) =>
      decideApproval(vars.projectId, vars.gateId, vars.status, vars.notes),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["approvals", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["project", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["runs", vars.projectId] });
      qc.invalidateQueries({ queryKey: ["agent-status"] });
    },
  });
}
