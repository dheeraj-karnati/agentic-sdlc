"use client";

import { CheckCircle2, XCircle, FileText, Code, Music, Video, Table2, Image, Archive, Database, Layers, BookOpen, GitBranch, Sparkles, AlertTriangle } from "lucide-react";
import { QualityScore } from "./quality-score";

/* eslint-disable @typescript-eslint/no-explicit-any */

const FILE_ICONS: Record<string, typeof FileText> = {
  document: FileText, source_code: Code, audio: Music, video: Video,
  spreadsheet: Table2, image: Image, archive: Archive, database_schema: Database,
};

const TYPE_BADGES: Record<string, { label: string; cls: string }> = {
  document: { label: "Document", cls: "bg-blue-500/15 text-blue-400" },
  source_code: { label: "Source code", cls: "bg-green-500/15 text-green-400" },
  audio: { label: "Audio recording", cls: "bg-amber-500/15 text-amber-400" },
  video: { label: "Video recording", cls: "bg-purple-500/15 text-purple-400" },
  spreadsheet: { label: "Spreadsheet", cls: "bg-teal-500/15 text-teal-400" },
  image: { label: "Image", cls: "bg-pink-500/15 text-pink-400" },
  archive: { label: "Archive", cls: "bg-gray-500/15 text-gray-400" },
  database_schema: { label: "Database schema", cls: "bg-indigo-500/15 text-indigo-400" },
};

function contentLabel(f: any): string {
  if (["audio", "video"].includes(f.file_type)) return "Transcribed";
  if (f.file_type === "image") return "Analyzed";
  if (f.file_type === "spreadsheet") return `${(f.word_count ?? 0).toLocaleString()} entries`;
  return `${(f.word_count ?? 0).toLocaleString()} words`;
}

export function IngestReport({ output }: { output: Record<string, any> }) {
  const metrics = output.metrics ?? {};
  const files = (output.processed_files ?? []) as any[];
  const quality = output.quality_assessment ?? {};
  const warnings = (quality.warnings ?? []) as string[];
  const projectType = output.project_type;
  const typeBreakdown = output.type_breakdown ?? {};
  const score = metrics.quality_score ?? quality.score ?? 0;
  const totalWords = metrics.words_extracted ?? 0;
  const totalFiles = metrics.files_processed ?? files.length;
  const failedCount = files.filter((f: any) => f.status === "failed").length;

  return (
    <div className="space-y-5">
      {/* ── Section 1: Summary banner ── */}
      <div className="border-l-4 border-emerald-500 bg-ink-900 rounded-r-lg p-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">Ingestion complete</h2>
          <p className="text-sm text-ink-300 mt-1">
            {failedCount === 0
              ? "All files have been processed and are ready for analysis."
              : `${totalFiles - failedCount} of ${totalFiles} files processed successfully.`}
          </p>
        </div>
        {score > 0 && <QualityScore score={score} size={72} />}
      </div>

      {/* ── Section 2: What we received ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <h3 className="text-sm font-semibold mb-1">Sources received</h3>
        <p className="text-xs text-ink-300 mb-4">{totalFiles} files uploaded &bull; {totalWords.toLocaleString()} total words extracted</p>

        <div className="border border-ink-700 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-ink-950 text-ink-300 text-left text-xs">
                <th className="px-4 py-2.5 font-medium">File</th>
                <th className="px-4 py-2.5 font-medium">Type</th>
                <th className="px-4 py-2.5 font-medium">Content</th>
                <th className="px-4 py-2.5 font-medium text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f: any, i: number) => {
                const Icon = FILE_ICONS[f.file_type] ?? FileText;
                const badge = TYPE_BADGES[f.file_type] ?? TYPE_BADGES.document;
                return (
                  <tr key={i} className="border-t border-ink-700">
                    <td className="px-4 py-2.5 flex items-center gap-2">
                      <Icon className="w-4 h-4 text-ink-400 shrink-0" />
                      <span className="truncate max-w-[200px]">{f.filename}</span>
                    </td>
                    <td className="px-4 py-2.5"><span className={`text-xs px-2 py-0.5 rounded ${badge.cls}`}>{badge.label}</span></td>
                    <td className="px-4 py-2.5 text-ink-300 text-xs">{contentLabel(f)}</td>
                    <td className="px-4 py-2.5 text-center">
                      {f.status === "processed" ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-500"><CheckCircle2 className="w-3.5 h-3.5" /> Processed</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-red-500"><XCircle className="w-3.5 h-3.5" /> Failed</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Section 3: What we found ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <h3 className="text-sm font-semibold mb-4">Analysis overview</h3>
        <div className="grid grid-cols-3 gap-3">
          {/* Project type */}
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              {projectType === "legacy_modernization" ? <GitBranch className="w-4 h-4 text-sky-500" /> : <Sparkles className="w-4 h-4 text-flame" />}
              <span className="text-xs text-ink-300">Project type</span>
            </div>
            <p className="text-sm font-semibold">{projectType === "legacy_modernization" ? "Legacy modernization" : "New project"}</p>
            <p className="text-[11px] text-ink-400 mt-1">
              {projectType === "legacy_modernization" ? "Source code detected — existing system will be analyzed" : "No existing code — requirements will guide a new build"}
            </p>
          </div>

          {/* Source diversity */}
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 text-sky-500" />
              <span className="text-xs text-ink-300">Source diversity</span>
            </div>
            <p className="text-sm font-semibold">{Object.keys(typeBreakdown).length} source types</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {Object.keys(typeBreakdown).map((t) => (
                <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-ink-700 text-ink-300">{TYPE_BADGES[t]?.label ?? t}</span>
              ))}
            </div>
          </div>

          {/* Volume */}
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-4 h-4 text-sky-500" />
              <span className="text-xs text-ink-300">Content volume</span>
            </div>
            <p className="text-sm font-semibold">{totalWords.toLocaleString()} words</p>
            <div className="mt-2 h-1.5 bg-ink-700 rounded-full overflow-hidden">
              <div className="h-full bg-sky-500 rounded-full transition-all" style={{ width: `${Math.min((quality.volume ?? 0), 100)}%` }} />
            </div>
          </div>
        </div>

        <p className="text-xs text-ink-300 mt-3">
          {Object.entries(typeBreakdown).map(([t, c]) => `${c} ${TYPE_BADGES[t]?.label.toLowerCase() ?? t}${(c as number) > 1 ? "s" : ""}`).join(", ")}
        </p>
      </div>

      {/* ── Section 4: Quality assessment ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <h3 className="text-sm font-semibold mb-1">Readiness assessment</h3>
        <p className="text-xs text-ink-300 mb-4">How well-prepared are these inputs for the Discovery agent</p>

        <div className="space-y-3">
          {[
            { label: "Completeness", value: quality.completeness ?? 0 },
            { label: "Diversity", value: quality.diversity ?? 0 },
            { label: "Volume", value: quality.volume ?? 0 },
          ].map((d) => (
            <div key={d.label} className="flex items-center gap-3">
              <span className="text-xs text-ink-300 w-24">{d.label}</span>
              <div className="flex-1 h-2 bg-ink-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${d.value >= 80 ? "bg-emerald-500" : d.value >= 60 ? "bg-amber-500" : "bg-red-500"}`}
                  style={{ width: `${Math.min(d.value, 100)}%` }}
                />
              </div>
              <span className="text-xs text-ink-300 w-12 text-right">{d.value}/100</span>
            </div>
          ))}
        </div>

        {warnings.length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-center gap-2 mb-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              <span className="text-xs font-medium text-amber-500">Warnings</span>
            </div>
            {warnings.map((w, i) => <p key={i} className="text-xs text-amber-500/80 ml-5">{w}</p>)}
          </div>
        )}

        <p className={`text-xs mt-3 font-medium ${score >= 80 ? "text-emerald-500" : score >= 60 ? "text-amber-500" : "text-red-500"}`}>
          {score >= 80 ? "Inputs are well-prepared. Ready to proceed." : score >= 60 ? "Inputs are adequate. Consider adding more sources for better results." : "Inputs may be insufficient. Adding more sources is recommended."}
        </p>
      </div>
    </div>
  );
}
