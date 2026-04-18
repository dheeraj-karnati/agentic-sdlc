"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { PlusCircle, ChevronDown, ChevronRight, Upload, X, Loader2, Lightbulb } from "lucide-react";
import { uploadFiles } from "@/lib/api-client";
import axios from "axios";

/* eslint-disable @typescript-eslint/no-explicit-any */

interface ImproveAnalysisProps {
  projectId: string;
  currentMetrics: { quality_score: number; completeness: number; diversity: number; volume: number };
  currentFileCount: number;
}

function getSuggestions(m: { quality_score: number; completeness: number; diversity: number; volume: number }): { text: string; suggest: string }[] {
  const suggestions: { text: string; suggest: string }[] = [];
  if (m.diversity < 70) suggestions.push({ text: "Your sources are limited in type diversity.", suggest: "Try adding: meeting recordings, technical specs, database schemas, or API documentation" });
  if (m.completeness < 70) suggestions.push({ text: "Some areas may lack sufficient detail.", suggest: "Try adding: detailed requirements documents, user stories, or process flow diagrams" });
  if (m.volume < 50) suggestions.push({ text: "Total content volume is low for thorough analysis.", suggest: "Try adding: more comprehensive documentation or existing source code" });
  return suggestions;
}

export function ImproveAnalysis({ projectId, currentMetrics, currentFileCount }: ImproveAnalysisProps) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = getSuggestions(currentMetrics);
  const isGood = currentMetrics.quality_score >= 85;

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function handleAddAndReanalyze() {
    if (files.length === 0) return;
    setLoading(true);
    try {
      await uploadFiles(projectId, files);
      const { data } = await axios.post(`${apiBase}/api/projects/${projectId}/agents/ingest/restart`);
      router.push(`/projects/${projectId}?runId=${data.run_id}`);
    } catch (e) {
      console.error("Re-analyze failed:", e);
      setLoading(false);
    }
  }

  return (
    <div className="border border-d8x-border rounded-lg overflow-hidden">
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between px-4 py-3 bg-d8x-surface hover:bg-d8x-surface-hover transition-colors text-left">
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown className="w-4 h-4 text-d8x-text-tertiary" /> : <ChevronRight className="w-4 h-4 text-d8x-text-tertiary" />}
          <PlusCircle className="w-4 h-4 text-d8x-blue" />
          <span className="text-sm font-medium">Add more sources to improve analysis</span>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-d8x-border text-d8x-text-secondary">{currentMetrics.quality_score}/100</span>
      </button>

      {expanded && (
        <div className="px-4 py-4 border-t border-d8x-border space-y-4">
          {/* Suggestions */}
          {isGood ? (
            <div className="flex items-start gap-2 p-3 bg-d8x-success/5 border border-d8x-success/20 rounded-lg">
              <Lightbulb className="w-4 h-4 text-d8x-success mt-0.5 shrink-0" />
              <p className="text-xs text-d8x-success">Your sources look comprehensive. Adding more files is optional but may uncover additional insights.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {suggestions.map((s, i) => (
                <div key={i} className="flex items-start gap-2 p-3 bg-d8x-warning/5 border border-d8x-warning/20 rounded-lg">
                  <Lightbulb className="w-4 h-4 text-d8x-warning mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs text-d8x-text-primary">{s.text}</p>
                    <p className="text-xs text-d8x-text-secondary mt-0.5">{s.suggest}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Compact upload zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); setFiles((prev) => [...prev, ...Array.from(e.dataTransfer.files)]); }}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all ${isDragging ? "border-d8x-blue bg-d8x-blue/5" : "border-d8x-border hover:border-d8x-border-hover"}`}
          >
            <Upload className="w-5 h-5 mx-auto text-d8x-text-tertiary mb-1" />
            <p className="text-xs text-d8x-text-secondary">Drop files here or <span className="text-d8x-blue">browse</span></p>
            <input ref={inputRef} type="file" multiple className="hidden" onChange={(e) => e.target.files && setFiles((prev) => [...prev, ...Array.from(e.target.files!)])} />
          </div>

          {/* New file list */}
          {files.length > 0 && (
            <div className="border border-d8x-border rounded-lg divide-y divide-d8x-border">
              {files.map((f, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                  <span className="truncate flex-1">{f.name}</span>
                  <button onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))} className="text-d8x-text-tertiary hover:text-d8x-danger ml-2"><X className="w-3.5 h-3.5" /></button>
                </div>
              ))}
            </div>
          )}

          {/* Action button */}
          <button
            onClick={handleAddAndReanalyze}
            disabled={files.length === 0 || loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-d8x-blue hover:bg-d8x-blue-light text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
            {loading ? "Re-analyzing..." : `Add ${files.length} file${files.length !== 1 ? "s" : ""} & re-analyze`}
          </button>
        </div>
      )}
    </div>
  );
}
