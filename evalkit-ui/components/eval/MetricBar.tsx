"use client";

import { cn } from "@/lib/utils";

interface MetricBarProps {
  label: string;
  value: number | null;
  max?: number;
}

function barColor(value: number): string {
  if (value > 0.7) return "bg-emerald-500";
  if (value >= 0.3) return "bg-amber-500";
  return "bg-red-500";
}

export function MetricBar({ label, value, max = 1 }: MetricBarProps) {
  const normalized = value !== null ? Math.min(value / max, 1) : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        {value !== null ? (
          <span className="font-mono text-slate-100">{value.toFixed(2)}</span>
        ) : (
          <span className="font-mono text-slate-500">N/A</span>
        )}
      </div>
      <div className="h-2 rounded-full bg-slate-900">
        {value !== null && (
          <div
            className={cn("h-full rounded-full transition-all", barColor(value / max))}
            style={{ width: `${normalized * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}
