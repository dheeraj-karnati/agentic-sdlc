import { cn } from "@/lib/utils";
import type { ProjectStatus, RunStatus } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  created: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  pending: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  running: "bg-d8x-blue/10 text-d8x-blue-light border-d8x-blue/20 animate-pulse",
  ingest: "bg-d8x-blue/10 text-d8x-blue-light border-d8x-blue/20",
  discover: "bg-d8x-blue/10 text-d8x-blue-light border-d8x-blue/20",
  design: "bg-d8x-blue/10 text-d8x-blue-light border-d8x-blue/20",
  prototype: "bg-d8x-gold/10 text-d8x-gold border-d8x-gold/20",
  plan: "bg-d8x-gold/10 text-d8x-gold border-d8x-gold/20",
  build: "bg-d8x-blue/10 text-d8x-blue-light border-d8x-blue/20",
  test: "bg-d8x-blue/10 text-d8x-blue-light border-d8x-blue/20",
  ship: "bg-d8x-blue/10 text-d8x-blue-light border-d8x-blue/20",
  completed: "bg-d8x-success/10 text-d8x-success border-d8x-success/20",
  failed: "bg-d8x-danger/10 text-d8x-danger border-d8x-danger/20",
  paused_for_input: "bg-d8x-warning/10 text-d8x-warning border-d8x-warning/20",
  paused_for_approval: "bg-d8x-warning/10 text-d8x-warning border-d8x-warning/20",
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
