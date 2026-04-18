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
  completed: "border-d8x-success/50 bg-d8x-success/5 text-d8x-success",
  active: "border-d8x-gold/50 bg-d8x-gold/5 text-d8x-gold animate-stage-pulse",
  paused: "border-d8x-warning/50 bg-d8x-warning/5 text-d8x-warning",
  upcoming: "border-d8x-border bg-d8x-surface text-d8x-text-secondary",
  failed: "border-d8x-danger/50 bg-d8x-danger/5 text-d8x-danger",
  unavailable: "border-d8x-border bg-d8x-surface text-d8x-text-tertiary opacity-50",
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
