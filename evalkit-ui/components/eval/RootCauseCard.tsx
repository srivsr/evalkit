"use client";

import { cn } from "@/lib/utils";
import type { RootCause } from "@/lib/types";
import { SeverityPill } from "./SeverityPill";

interface RootCauseCardProps {
  rootCause: RootCause;
  label?: string;
}

const borderColorMap: Record<string, string> = {
  blocker: "border-l-red-500",
  critical: "border-l-red-400",
  major: "border-l-amber-500",
  minor: "border-l-slate-500",
  none: "border-l-emerald-500",
};

export function RootCauseCard({ rootCause, label }: RootCauseCardProps) {
  const borderColor = borderColorMap[rootCause.severity] ?? "border-l-slate-500";

  return (
    <div
      className={cn(
        "rounded-lg border border-slate-800 bg-slate-900 p-5 border-l-4 space-y-3",
        borderColor
      )}
    >
      {label && (
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
          {label}
        </span>
      )}
      <div className="flex items-center gap-3">
        <code className="text-lg font-mono font-semibold text-slate-100">
          {rootCause.code}
        </code>
        <SeverityPill severity={rootCause.severity} />
      </div>
      <p className="text-sm text-slate-300">{rootCause.message}</p>
      <span className="inline-block rounded-md bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 border border-slate-700">
        {rootCause.attribution}
      </span>
    </div>
  );
}
