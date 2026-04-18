"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface OutputSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  count?: number;
}

export function OutputSection({ title, children, defaultExpanded = false, count }: OutputSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="border border-d8x-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-d8x-surface hover:bg-d8x-surface-hover transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown className="w-4 h-4 text-d8x-text-tertiary" /> : <ChevronRight className="w-4 h-4 text-d8x-text-tertiary" />}
          <span className="text-sm font-medium">{title}</span>
          {count !== undefined && (
            <span className="text-xs bg-d8x-border px-1.5 py-0.5 rounded text-d8x-text-secondary">{count}</span>
          )}
        </div>
      </button>
      {expanded && <div className="px-4 py-3 border-t border-d8x-border text-sm">{children}</div>}
    </div>
  );
}
