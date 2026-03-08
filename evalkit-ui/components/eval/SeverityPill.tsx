"use client";

import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

interface SeverityPillProps {
  severity: string;
}

const colorMap: Record<string, string> = {
  blocker: "bg-red-900 text-red-100",
  critical: "bg-red-600 text-white",
  major: "bg-amber-600 text-white",
  minor: "bg-slate-600 text-slate-200",
  none: "bg-emerald-600 text-white",
};

export function SeverityPill({ severity }: SeverityPillProps) {
  const colors = colorMap[severity] ?? "bg-slate-500 text-white";

  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-xs font-mono uppercase",
        colors
      )}
    >
      {severity}
    </span>
  );
}
