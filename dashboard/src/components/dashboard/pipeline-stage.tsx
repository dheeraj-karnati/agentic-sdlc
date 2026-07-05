"use client";

import { cn } from "@/lib/utils";
import { Check, X, Eye, Lock, Loader2 } from "lucide-react";
import type { RunStatus } from "@/lib/types";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export type StageStatus = "completed" | "active" | "paused" | "upcoming" | "failed" | "unavailable";

interface PipelineStageProps {
  num: string;
  label: string;
  status: StageStatus;
  available: boolean;
  onClick?: () => void;
}

const STATUS_CLASSES: Record<StageStatus, string> = {
  completed: "border-emerald-500/50 bg-emerald-500/5 text-emerald-500",
  active: "border-flame/50 bg-flame/5 text-flame animate-stage-pulse",
  paused: "border-amber-500/50 bg-amber-500/5 text-amber-500",
  upcoming: "border-ink-700 bg-ink-900 text-ink-300",
  failed: "border-red-500/50 bg-red-500/5 text-red-500",
  unavailable: "border-ink-700 bg-ink-900 text-ink-400 opacity-50",
};

function StatusIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "completed": return <Check className="w-3.5 h-3.5" />;
    case "active": return <Loader2 className="w-3.5 h-3.5 animate-spin" />;
    case "paused": return <Eye className="w-3.5 h-3.5" />;
    case "failed": return <X className="w-3.5 h-3.5" />;
    case "unavailable": return <Lock className="w-3 h-3" />;
    default: return null;
  }
}

export function PipelineStage({ num, label, status, available, onClick }: PipelineStageProps) {
  const stage = (
    <button
      onClick={available ? onClick : undefined}
      disabled={!available}
      className={cn(
        "flex flex-col items-center gap-1 px-3 py-2 rounded-lg border transition-all min-w-[72px]",
        available && status !== "unavailable" ? "cursor-pointer hover:brightness-110" : "cursor-default",
        STATUS_CLASSES[status],
      )}
    >
      <div className="flex items-center gap-1">
        <span className="text-[10px] font-mono opacity-70">{num}</span>
        <StatusIcon status={status} />
      </div>
      <span className="text-xs font-medium">{label}</span>
    </button>
  );

  if (!available) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{stage}</TooltipTrigger>
          <TooltipContent side="bottom"><p className="text-xs">Coming soon</p></TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return stage;
}
