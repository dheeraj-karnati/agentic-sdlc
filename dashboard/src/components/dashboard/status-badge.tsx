import { cn } from "@/lib/utils";
import type { ProjectStatus, RunStatus } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  created: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  pending: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  running: "bg-sky-500/10 text-sky-400 border-sky-500/20 animate-pulse",
  ingest: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  discover: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  design: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  prototype: "bg-flame/10 text-flame border-flame/20",
  plan: "bg-flame/10 text-flame border-flame/20",
  build: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  test: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  ship: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  completed: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  failed: "bg-red-500/10 text-red-500 border-red-500/20",
  paused_for_input: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  paused_for_approval: "bg-amber-500/10 text-amber-500 border-amber-500/20",
};

export function StatusBadge({ status }: { status: ProjectStatus | RunStatus }) {
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border", STATUS_STYLES[status] ?? STATUS_STYLES.created)}>
      {(status === "running") && <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5" />}
      {label}
    </span>
  );
}
