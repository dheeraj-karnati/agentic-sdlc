import { useQuery } from "@tanstack/react-query";
import { listRuns } from "../api-client";
import type { AgentType } from "../types";

export function useRuns(projectId: string) {
  return useQuery({
    queryKey: ["runs", projectId],
    queryFn: () => listRuns(projectId),
    enabled: !!projectId,
    refetchInterval: 5000, // poll for new runs
  });
}

export function useLatestRunByAgent(projectId: string, agentType: AgentType | null) {
  const { data: runs, ...rest } = useRuns(projectId);
  const latestRun = agentType
    ? runs?.find((r) => r.agent_type === agentType)
    : undefined;
  return { data: latestRun, runs, ...rest };
}
