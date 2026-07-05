import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  className?: string;
}

export function MetricCard({ label, value, icon: Icon, className }: MetricCardProps) {
  return (
    <div className={cn("bg-ink-900 border border-ink-700 rounded-lg p-4 animate-fade-up", className)}>
      <div className="flex items-center justify-between">
        <span className="text-2xl font-bold text-ink-50">{value}</span>
        {Icon && <Icon className="w-5 h-5 text-ink-400" />}
      </div>
      <p className="text-xs text-ink-300 mt-1">{label}</p>
    </div>
  );
}
