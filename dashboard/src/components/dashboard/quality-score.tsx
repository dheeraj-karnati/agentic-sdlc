"use client";

import { cn } from "@/lib/utils";

export function QualityScore({ score, size = 100 }: { score: number; size?: number }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? "#27AE60" : score >= 60 ? "#F39C12" : "#E74C3C";

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#30363D" strokeWidth={6} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={6} strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
        <text
          x={size / 2} y={size / 2}
          textAnchor="middle" dominantBaseline="central"
          className="rotate-90 origin-center fill-ink-50 text-xl font-bold"
          style={{ transformOrigin: `${size / 2}px ${size / 2}px` }}
        >
          {Math.round(score)}
        </text>
      </svg>
      <span className="text-xs text-ink-300">Quality Score</span>
    </div>
  );
}
