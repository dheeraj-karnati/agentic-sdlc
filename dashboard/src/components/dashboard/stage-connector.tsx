import { cn } from "@/lib/utils";

export function StageConnector({ isActive }: { isActive: boolean }) {
  return (
    <div className="flex items-center mx-0.5 relative w-8">
      <div className="w-full h-px bg-ink-700" />
      {isActive && (
        <div className="absolute inset-0 flex items-center overflow-hidden">
          <div className="w-2 h-2 rounded-full bg-flame animate-dot-flow" />
        </div>
      )}
    </div>
  );
}
