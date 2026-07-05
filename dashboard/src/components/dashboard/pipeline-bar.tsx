"use client";

import { AGENTS, getCompletedAgents, STATUS_TO_AGENT } from "@/lib/types";
import type { AgentType, ProjectStatus, RunStatus } from "@/lib/types";
import { PipelineStage, type StageStatus } from "./pipeline-stage";
import { StageConnector } from "./stage-connector";

interface PipelineBarProps {
  projectStatus: ProjectStatus;
  activeRunStatus?: RunStatus;
  onStageClick?: (agentType: AgentType) => void;
}

function getStageStatus(
  agentId: AgentType,
  projectStatus: ProjectStatus,
  activeRunStatus?: RunStatus,
  completed?: AgentType[],
): StageStatus {
  if (completed?.includes(agentId)) return "completed";
  const current = STATUS_TO_AGENT[projectStatus];
  if (current === agentId) {
    if (activeRunStatus === "running" || activeRunStatus === "pending") return "active";
    if (activeRunStatus === "paused_for_input" || activeRunStatus === "paused_for_approval") return "paused";
    if (activeRunStatus === "failed") return "failed";
    if (activeRunStatus === "completed") return "completed";
    return "active";
  }
  const agent = AGENTS.find((a) => a.id === agentId);
  if (!agent?.available) return "unavailable";
  return "upcoming";
}

export function PipelineBar({ projectStatus, activeRunStatus, onStageClick }: PipelineBarProps) {
  const completed = getCompletedAgents(projectStatus);
  const currentAgent = STATUS_TO_AGENT[projectStatus];

  return (
    <div className="flex items-center justify-center gap-0 px-4 py-4 bg-ink-900 border-b border-ink-700 overflow-x-auto">
      {AGENTS.map((agent, i) => {
        const status = getStageStatus(agent.id, projectStatus, activeRunStatus, completed);
        const nextStatus = i < AGENTS.length - 1
          ? getStageStatus(AGENTS[i + 1].id, projectStatus, activeRunStatus, completed)
          : undefined;

        return (
          <div key={agent.id} className="flex items-center animate-fade-in" style={{ animationDelay: `${i * 0.08}s` }}>
            <PipelineStage
              num={agent.num}
              label={agent.label}
              status={status}
              available={agent.available}
              onClick={() => onStageClick?.(agent.id)}
            />
            {i < AGENTS.length - 1 && <StageConnector isActive={nextStatus === "active"} />}
          </div>
        );
      })}
    </div>
  );
}
