import Link from "next/link";
import { Plus } from "lucide-react";

function D8XLogo() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="1.5" y="1.5" width="21" height="21" rx="4" stroke="currentColor" strokeOpacity=".5" strokeWidth="1.4"/>
      <circle cx="9.5" cy="9.5" r="2.4" stroke="#ff7a3a" strokeWidth="1.6"/>
      <circle cx="14.5" cy="14.5" r="2.4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M14.5 9.5h2.5M9.5 14.5H7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

export function Topbar({ projectName }: { projectName?: string }) {
  return (
    <header className="h-14 border-b border-ink-700 bg-ink-900 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-3">
        <Link href="/projects" className="flex items-center gap-2">
          <D8XLogo />
          <span className="display text-[17px] font-semibold tracking-tight">D8X</span>
          <span className="text-[11px] text-ink-400 ml-0.5 hidden sm:inline uppercase tracking-wider">Mission Control</span>
        </Link>
        {projectName && (
          <>
            <span className="text-ink-500">/</span>
            <span className="text-sm text-ink-50 font-medium truncate max-w-[300px]">{projectName}</span>
          </>
        )}
      </div>
      <Link
        href="/projects/new"
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-flame/10 text-flame border border-flame/20 rounded-md hover:bg-flame/20 transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
        New Analysis
      </Link>
    </header>
  );
}
