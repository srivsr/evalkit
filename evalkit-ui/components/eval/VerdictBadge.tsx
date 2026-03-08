"use client";

import { cn } from "@/lib/utils";
import type { Verdict } from "@/lib/types";

interface VerdictBadgeProps {
  verdict: string;
  size?: "sm" | "lg";
}

const colorMap: Record<string, string> = {
  PASS: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  FAIL: "bg-red-500/10 text-red-400 border-red-500/20",
  WARN: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

const dotColorMap: Record<string, string> = {
  PASS: "bg-emerald-400",
  FAIL: "bg-red-400",
  WARN: "bg-amber-400",
};

export function VerdictBadge({ verdict, size = "sm" }: VerdictBadgeProps) {
  const colors = colorMap[verdict] ?? "bg-slate-500/10 text-slate-400 border-slate-500/20";
  const dotColor = dotColorMap[verdict] ?? "bg-slate-400";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-semibold border rounded-md",
        colors,
        size === "lg" ? "text-lg px-4 py-2" : "text-xs px-2 py-0.5"
      )}
    >
      <span className={cn("rounded-full shrink-0", dotColor, size === "lg" ? "h-2.5 w-2.5" : "h-1.5 w-1.5")} />
      {verdict}
    </span>
  );
}
