"use client";

import { useState } from "react";
import { Download, FileText, FileSpreadsheet, Loader2, ChevronDown } from "lucide-react";

interface ReportDownloadProps {
  projectId: string;
  agentType: string;
}

export function ReportDownload({ projectId, agentType }: ReportDownloadProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  async function handleDownload(format: "pdf" | "docx") {
    setLoading(format);
    setOpen(false);
    try {
      const resp = await fetch(`${apiBase}/api/projects/${projectId}/reports/${agentType}?format=${format}`);
      if (!resp.ok) throw new Error("Download failed");
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `D8X-${agentType}-report-${projectId.slice(0, 8)}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download failed:", e);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-ink-300 border border-ink-700 rounded-md hover:bg-ink-850 transition-colors"
      >
        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
        Download report
        <ChevronDown className="w-3 h-3" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 w-44 bg-ink-900 border border-ink-700 rounded-lg shadow-xl z-20 overflow-hidden">
            <button onClick={() => handleDownload("pdf")} className="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-ink-50 hover:bg-ink-850 transition-colors">
              <FileText className="w-4 h-4 text-red-400" /> PDF report
            </button>
            <button onClick={() => handleDownload("docx")} className="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-ink-50 hover:bg-ink-850 transition-colors border-t border-ink-700">
              <FileSpreadsheet className="w-4 h-4 text-blue-400" /> Word document
            </button>
          </div>
        </>
      )}
    </div>
  );
}
