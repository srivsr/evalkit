"use client";

import { cn } from "@/lib/utils";
import type { FixSuggestion } from "@/lib/types";

interface FixSuggestionsProps {
  suggestions: FixSuggestion[];
}

const priorityDot: Record<string, string> = {
  high: "bg-red-400",
  medium: "bg-amber-400",
  low: "bg-emerald-400",
};

export function FixSuggestions({ suggestions }: FixSuggestionsProps) {
  if (suggestions.length === 0) return null;

  return (
    <div className="space-y-3">
      {suggestions.map((suggestion, i) => (
        <div
          key={`${suggestion.target}-${i}`}
          className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-2"
        >
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "h-2 w-2 rounded-full shrink-0",
                priorityDot[suggestion.priority] ?? "bg-slate-400"
              )}
            />
            <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-mono text-slate-300">
              {suggestion.target}
            </span>
          </div>
          <p className="text-sm text-slate-100">{suggestion.action}</p>
          {suggestion.detail && (
            <p className="text-xs text-slate-400">{suggestion.detail}</p>
          )}
        </div>
      ))}
    </div>
  );
}
