"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, RotateCcw, XCircle, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { decideApproval, startAgent } from "@/lib/api-client";
import { Textarea } from "@/components/ui/textarea";
import type { AgentType } from "@/lib/types";

const NEXT_LABELS: Partial<Record<AgentType, string>> = {
  ingest: "Discovery", discover: "Design", design: "Prototype",
  prototype: "Planning", plan: "Build", build: "Test", test: "Ship",
};

const NEXT_AGENT_TYPE: Partial<Record<AgentType, AgentType>> = {
  ingest: "discover", discover: "design", design: "prototype",
  prototype: "plan", plan: "build", build: "test", test: "ship",
};

interface ApprovalActionsProps {
  projectId: string;
  gateId: string;
  agentType: AgentType;
}

export function ApprovalActions({ projectId, gateId, agentType }: ApprovalActionsProps) {
  const router = useRouter();
  const qc = useQueryClient();
  const [showRevision, setShowRevision] = useState(false);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [decision, setDecision] = useState<string | null>(null);

  const nextLabel = NEXT_LABELS[agentType] ?? "next agent";

  async function invalidateAll() {
    qc.invalidateQueries({ queryKey: ["project", projectId] });
    qc.invalidateQueries({ queryKey: ["approvals", projectId] });
    qc.invalidateQueries({ queryKey: ["agent-status"] });
    qc.invalidateQueries({ queryKey: ["agent-status-poll"] });
    qc.invalidateQueries({ queryKey: ["latest-run", projectId] });
    qc.invalidateQueries({ queryKey: ["runs", projectId] });
  }

  async function handleApprove() {
    setSubmitting(true);
    try {
      const result = await decideApproval(projectId, gateId, "approved");
      setDecision("approved");
      await invalidateAll();

      const data = result as any;
      let runId = data?.next_run_id;

      // If the backend created a run but the background task might not start,
      // explicitly call the start endpoint for the next agent as a fallback
      const nextType = NEXT_AGENT_TYPE[agentType];
      if (nextType) {
        try {
          const startResult = await startAgent(projectId, nextType);
          if (startResult?.run_id) runId = startResult.run_id;
        } catch (startErr) {
          // Agent may already be running from backend auto-start — that's fine
          console.log("Start agent fallback (may already be running):", startErr);
        }
      }

      // Wait a moment then hard-navigate
      await new Promise((r) => setTimeout(r, 1000));
      window.location.href = runId
        ? `/projects/${projectId}?runId=${runId}`
        : `/projects/${projectId}`;
    } catch (e) {
      console.error("Approve failed:", e);
      setSubmitting(false);
    }
  }

  async function handleRevise() {
    if (!notes.trim()) return;
    setSubmitting(true);
    try {
      await decideApproval(projectId, gateId, "revision_requested", notes);
      setDecision("revision_requested");
      await invalidateAll();
    } catch (e) {
      console.error("Revise failed:", e);
      setSubmitting(false);
    }
  }

  async function handleReject() {
    if (!confirm("Are you sure? This will discard the results and return to the upload screen.")) return;
    setSubmitting(true);
    try {
      await decideApproval(projectId, gateId, "rejected");
      setDecision("rejected");
      await invalidateAll();
      router.push("/projects/new");
    } catch (e) {
      console.error("Reject failed:", e);
      setSubmitting(false);
    }
  }

  // Decision made — show confirmation
  if (decision) {
    const msgs: Record<string, { cls: string; text: string }> = {
      approved: { cls: "bg-emerald-500/10 border-emerald-500/30 text-emerald-500", text: `Approved — starting ${nextLabel} agent...` },
      revision_requested: { cls: "bg-amber-500/10 border-amber-500/30 text-amber-500", text: "Reprocessing with your feedback..." },
      rejected: { cls: "bg-red-500/10 border-red-500/30 text-red-500", text: "Rejected — returning to upload" },
    };
    const m = msgs[decision] ?? msgs.approved;
    return (
      <div className={`mt-6 p-4 rounded-lg border flex items-center gap-3 ${m.cls}`}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm font-medium">{m.text}</span>
      </div>
    );
  }

  return (
    <div className="mt-6 pt-6 border-t border-ink-700">
      <p className="text-sm text-ink-300 italic mb-5">
        The next step is the {nextLabel} agent
        {agentType === "ingest" && ", which will analyze these sources for business rules, requirements, domain entities, and potential conflicts between different sources."}
        {agentType === "discover" && ", which will generate architecture decisions, database schema, API contracts, and frontend component design."}
        {agentType === "design" && ", which will create an interactive prototype at a live preview URL for stakeholder review."}
      </p>

      {!showRevision ? (
        <div className="flex gap-3">
          <button
            onClick={handleApprove}
            disabled={submitting}
            className="flex-[2] flex items-center justify-center gap-2 py-3 rounded-lg bg-emerald-500 hover:bg-emerald-500/90 text-white font-medium text-sm transition-colors disabled:opacity-50"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Approve & start {nextLabel}
          </button>
          <button
            onClick={() => setShowRevision(true)}
            disabled={submitting}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border border-amber-500/50 text-amber-500 hover:bg-amber-500/10 text-sm transition-colors disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            Request changes
          </button>
          <button
            onClick={handleReject}
            disabled={submitting}
            className="px-4 py-3 rounded-lg border border-red-500/30 text-red-500 hover:bg-red-500/10 text-sm transition-colors disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="bg-ink-900 border border-ink-700 rounded-lg p-4 space-y-3">
          <h4 className="text-sm font-medium">What should change?</h4>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Describe what needs to be different. For example: 'The PDF wasn't parsed correctly' or 'Please also process the ZIP file contents'"
            className="bg-ink-950 border-ink-700 min-h-[80px] text-sm"
          />
          <div className="flex gap-2">
            <button onClick={handleRevise} disabled={!notes.trim() || submitting} className="px-4 py-2 rounded-lg bg-amber-500 text-ink-950 text-sm font-medium disabled:opacity-50">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin inline mr-1" /> : null}
              Reprocess with feedback
            </button>
            <button onClick={() => setShowRevision(false)} className="px-4 py-2 rounded-lg bg-ink-900 border border-ink-700 text-ink-300 text-sm">Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
