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
    <div className={cn("bg-d8x-surface border border-d8x-border rounded-lg p-4 animate-fade-up", className)}>
      <div className="flex items-center justify-between">
        <span className="text-2xl font-bold text-d8x-text-primary">{value}</span>
        {Icon && <Icon className="w-5 h-5 text-d8x-text-tertiary" />}
      </div>
      <p className="text-xs text-d8x-text-secondary mt-1">{label}</p>
    </div>
  );
}
