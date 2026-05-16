"use client";

import type { Project, ApprovalGate } from "@/lib/types";
import { Clock, Info } from "lucide-react";

interface ActivitySidebarProps {
  project: Project;
  approvals: ApprovalGate[];
}

export function ActivitySidebar({ project, approvals }: ActivitySidebarProps) {
  const events = buildEvents(project, approvals);

  return (
    <aside className="border-l border-ink-700 bg-ink-900/50 p-5 space-y-6 h-full overflow-y-auto">
      {/* Project info */}
      <div>
        <h3 className="text-xs font-semibold text-ink-300 uppercase tracking-wider mb-3">Project</h3>
        <p className="text-sm font-medium">{project.name}</p>
        {project.description && <p className="text-xs text-ink-300 mt-1">{project.description}</p>}
        <div className="flex items-center gap-1.5 mt-3 text-xs text-ink-300">
          <Clock className="w-3 h-3" />
          Created {new Date(project.created_at).toLocaleDateString()}
        </div>
      </div>

      {/* Activity log */}
      <div>
        <h3 className="text-xs font-semibold text-ink-300 uppercase tracking-wider mb-3">Activity</h3>
        {events.length === 0 && (
          <p className="text-xs text-ink-400">No activity yet.</p>
        )}
        <div className="space-y-3">
          {events.map((e, i) => (
            <div key={i} className="flex gap-2 animate-fade-up" style={{ animationDelay: `${i * 0.05}s` }}>
              <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${e.color}`} />
              <div>
                <p className="text-xs">{e.text}</p>
                <p className="text-[10px] text-ink-400 mt-0.5">{e.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

interface Event { text: string; time: string; color: string }

function buildEvents(project: Project, approvals: ApprovalGate[]): Event[] {
  const events: Event[] = [];

  events.push({
    text: `Project "${project.name}" created`,
    time: new Date(project.created_at).toLocaleString(),
    color: "bg-sky-500",
  });

  for (const gate of approvals) {
    if (gate.status === "approved") {
      events.push({
        text: `${gate.agent_type ?? "Agent"} approved`,
        time: gate.decided_at ? new Date(gate.decided_at).toLocaleString() : "",
        color: "bg-emerald-500",
      });
    } else if (gate.status === "rejected") {
      events.push({
        text: `${gate.agent_type ?? "Agent"} rejected`,
        time: gate.decided_at ? new Date(gate.decided_at).toLocaleString() : "",
        color: "bg-red-500",
      });
    } else if (gate.status === "pending") {
      events.push({
        text: `${gate.agent_type ?? "Agent"} awaiting review`,
        time: new Date(gate.created_at).toLocaleString(),
        color: "bg-amber-500",
      });
    }
  }

  return events.reverse();
}
