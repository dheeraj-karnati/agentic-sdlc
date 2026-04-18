"use client";

import { useState } from "react";
import { Check, RotateCcw, X } from "lucide-react";
import { useDecideApproval } from "@/lib/hooks/use-approvals";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";

interface ApprovalControlsProps {
  projectId: string;
  gateId: string;
  onDecision?: () => void;
}

export function ApprovalControls({ projectId, gateId, onDecision }: ApprovalControlsProps) {
  const [showReviseDialog, setShowReviseDialog] = useState(false);
  const [notes, setNotes] = useState("");
  const decide = useDecideApproval();

  const handleApprove = () => {
    decide.mutate({ projectId, gateId, status: "approved" }, { onSuccess: onDecision });
  };

  const handleRevise = () => {
    decide.mutate({ projectId, gateId, status: "revision_requested", notes }, {
      onSuccess: () => { setShowReviseDialog(false); onDecision?.(); },
    });
  };

  const handleReject = () => {
    if (confirm("Are you sure you want to reject this agent's output?")) {
      decide.mutate({ projectId, gateId, status: "rejected" }, { onSuccess: onDecision });
    }
  };

  if (decide.isSuccess) {
    return <p className="text-sm text-d8x-text-secondary">Decision submitted.</p>;
  }

  return (
    <>
      <div className="flex items-center gap-3 pt-4 border-t border-d8x-border mt-4">
        <Button
          onClick={handleApprove}
          disabled={decide.isPending}
          className="bg-d8x-success hover:bg-d8x-success/90 text-white flex-1"
        >
          <Check className="w-4 h-4 mr-1.5" />
          Approve & Continue
        </Button>
        <Button
          variant="outline"
          onClick={() => setShowReviseDialog(true)}
          disabled={decide.isPending}
          className="border-d8x-warning text-d8x-warning hover:bg-d8x-warning/10"
        >
          <RotateCcw className="w-4 h-4 mr-1.5" />
          Request Changes
        </Button>
        <Button
          variant="ghost"
          onClick={handleReject}
          disabled={decide.isPending}
          className="text-d8x-danger hover:bg-d8x-danger/10"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      <Dialog open={showReviseDialog} onOpenChange={setShowReviseDialog}>
        <DialogContent className="bg-d8x-surface border-d8x-border">
          <DialogHeader>
            <DialogTitle>Request Changes</DialogTitle>
          </DialogHeader>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Describe what needs to change..."
            className="bg-d8x-background border-d8x-border min-h-[100px]"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReviseDialog(false)}>Cancel</Button>
            <Button onClick={handleRevise} disabled={!notes.trim()} className="bg-d8x-warning text-d8x-background hover:bg-d8x-warning/90">
              Submit Revision Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
