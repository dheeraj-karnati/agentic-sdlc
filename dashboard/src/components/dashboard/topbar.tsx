import Link from "next/link";
import { Plus } from "lucide-react";

export function Topbar({ projectName }: { projectName?: string }) {
  return (
    <header className="h-14 border-b border-d8x-border bg-d8x-surface flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-3">
        <Link href="/projects" className="flex items-center gap-1.5">
          <span className="text-lg font-black tracking-tighter">
            D8<span className="text-d8x-gold">X</span>
          </span>
          <span className="text-xs text-d8x-text-secondary ml-1 hidden sm:inline">Mission Control</span>
        </Link>
        {projectName && (
          <>
            <span className="text-d8x-text-tertiary">/</span>
            <span className="text-sm text-d8x-text-primary font-medium truncate max-w-[300px]">{projectName}</span>
          </>
        )}
      </div>
      <Link
        href="/projects/new"
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-d8x-gold/10 text-d8x-gold border border-d8x-gold/20 rounded-md hover:bg-d8x-gold/20 transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
        New Analysis
      </Link>
    </header>
  );
}
