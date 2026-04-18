import { useQuery } from "@tanstack/react-query";
import { listArtifacts } from "../api-client";

export function useArtifacts(projectId: string) {
  return useQuery({
    queryKey: ["artifacts", projectId],
    queryFn: () => listArtifacts(projectId),
    enabled: !!projectId,
  });
}
