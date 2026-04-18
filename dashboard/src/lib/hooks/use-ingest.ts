import { useMutation, useQueryClient } from "@tanstack/react-query";
import { importUrl, uploadFiles } from "../api-client";

export function useUploadFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { projectId: string; files: File[] }) => uploadFiles(vars.projectId, vars.files),
    onSuccess: (_, vars) => qc.invalidateQueries({ queryKey: ["project", vars.projectId] }),
  });
}

export function useImportUrl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { projectId: string; url: string }) => importUrl(vars.projectId, vars.url),
    onSuccess: (_, vars) => qc.invalidateQueries({ queryKey: ["project", vars.projectId] }),
  });
}
