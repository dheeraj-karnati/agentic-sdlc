"use client";

import Link from "next/link";
import { Plus, FolderOpen } from "lucide-react";
import { useProjects } from "@/lib/hooks/use-project";
import { StatusBadge } from "@/components/dashboard/status-badge";

export default function ProjectsPage() {
  const { data, isLoading, error } = useProjects();
  const projects = data?.projects ?? [];

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-sm text-ink-300 mt-1">Your D8X analyses</p>
        </div>
        <Link
          href="/projects/new"
          className="flex items-center gap-2 px-4 py-2.5 bg-flame text-ink-950 font-medium text-sm rounded-lg hover:bg-flame-soft transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Analysis
        </Link>
      </div>

      {isLoading && <p className="text-ink-300 text-sm">Loading...</p>}
      {error && <p className="text-red-500 text-sm">Failed to load projects. Is the API running?</p>}

      {!isLoading && projects.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-ink-900 border border-ink-700 flex items-center justify-center mb-6">
            <FolderOpen className="w-8 h-8 text-ink-400" />
          </div>
          <h2 className="text-lg font-semibold mb-2">No analyses yet</h2>
          <p className="text-sm text-ink-300 mb-6 max-w-sm">
            Upload your BRDs, source code, or recordings and watch 8 AI agents analyze, design, and build.
          </p>
          <Link
            href="/projects/new"
            className="flex items-center gap-2 px-5 py-2.5 bg-flame text-ink-950 font-medium text-sm rounded-lg hover:bg-flame-soft transition-colors"
          >
            <Plus className="w-4 h-4" />
            Start your first analysis
          </Link>
        </div>
      )}

      {projects.length > 0 && (
        <div className="border border-ink-700 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-ink-900 border-b border-ink-700 text-ink-300 text-left">
                <th className="px-4 py-3 font-medium">Project</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="border-b border-ink-700 last:border-0 hover:bg-ink-900/50 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/projects/${p.id}`} className="font-medium text-ink-50 hover:text-flame transition-colors">
                      {p.name}
                    </Link>
                    {p.description && <p className="text-xs text-ink-300 mt-0.5 truncate max-w-md">{p.description}</p>}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3 text-ink-300">{new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
