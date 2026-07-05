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
    <div className="border border-ink-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-ink-900 hover:bg-ink-850 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown className="w-4 h-4 text-ink-400" /> : <ChevronRight className="w-4 h-4 text-ink-400" />}
          <span className="text-sm font-medium">{title}</span>
          {count !== undefined && (
            <span className="text-xs bg-ink-700 px-1.5 py-0.5 rounded text-ink-300">{count}</span>
          )}
        </div>
      </button>
      {expanded && <div className="px-4 py-3 border-t border-ink-700 text-sm">{children}</div>}
    </div>
  );
}
