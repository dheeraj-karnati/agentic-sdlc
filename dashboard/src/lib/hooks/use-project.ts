import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createProject, getProject, listProjects } from "../api-client";

export function useProjects() {
  return useQuery({ queryKey: ["projects"], queryFn: listProjects });
}

export function useProject(id: string) {
  return useQuery({ queryKey: ["project", id], queryFn: () => getProject(id), enabled: !!id });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { name: string; description?: string }) => createProject(vars.name, vars.description),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}
