"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Play, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FileUploader } from "@/components/dashboard/file-uploader";
import { createProject, uploadFiles, startAgent } from "@/lib/api-client";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("");
  const [error, setError] = useState("");

  const canSubmit = name.trim().length > 0 && files.length > 0 && !loading;

  async function handleSubmit() {
    if (!canSubmit) return;
    setLoading(true);
    setError("");

    try {
      setLoadingText("Creating project...");
      const project = await createProject(name.trim(), description.trim() || undefined);

      setLoadingText(`Uploading ${files.length} file${files.length > 1 ? "s" : ""}...`);
      await uploadFiles(project.id, files);

      setLoadingText("Starting analysis...");
      const agentRun = await startAgent(project.id, "ingest");

      router.push(`/projects/${project.id}?runId=${agentRun.run_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong. Is the API running?");
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto px-6 py-12">
      <h1 className="text-2xl font-bold mb-2">New analysis</h1>
      <p className="text-sm text-ink-300 mb-8">Upload your project artifacts and let D8X analyze them.</p>

      {/* Project info */}
      <div className="space-y-4 mb-8">
        <div>
          <label className="text-sm font-medium text-ink-300 mb-1.5 block">Project name *</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Inventory system modernization"
            className="bg-ink-950 border-ink-700"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-ink-300 mb-1.5 block">Description</label>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of what you're analyzing..."
            className="bg-ink-950 border-ink-700 min-h-[80px]"
          />
        </div>
      </div>

      {/* File upload */}
      <div className="mb-8">
        <label className="text-sm font-medium text-ink-300 mb-3 block">Upload artifacts *</label>
        <FileUploader files={files} onFilesChange={setFiles} />
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-500">
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-ink-900 hover:bg-sky-500 text-white font-medium rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            {loadingText}
          </>
        ) : (
          <>
            <Play className="w-4 h-4" />
            Begin analysis
          </>
        )}
      </button>
    </div>
  );
}
