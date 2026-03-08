"use client";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { timeAgo, verdictColor } from "@/lib/utils";
import { ROOT_CAUSE_LABELS } from "@/lib/constants";
import type { EvaluationListItem } from "@/lib/types";
import { ExternalLink } from "lucide-react";

interface EvaluationTableProps {
  evaluations: EvaluationListItem[];
}

export function EvaluationTable({ evaluations }: EvaluationTableProps) {
  if (evaluations.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <p className="text-lg mb-2">No evaluations yet</p>
        <p className="text-sm">Run your first evaluation to see results here.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-slate-400 text-left">
            <th className="py-3 px-4 font-medium">Run ID</th>
            <th className="py-3 px-4 font-medium">Verdict</th>
            <th className="py-3 px-4 font-medium">Root Cause</th>
            <th className="py-3 px-4 font-medium">Created</th>
            <th className="py-3 px-4 font-medium w-16"></th>
          </tr>
        </thead>
        <tbody>
          {evaluations.map((eval_item) => (
            <tr
              key={eval_item.run_id}
              className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
            >
              <td className="py-3 px-4 font-mono text-xs text-slate-300">
                {eval_item.run_id.substring(0, 12)}...
              </td>
              <td className="py-3 px-4">
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border",
                    eval_item.verdict === "PASS" && "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                    eval_item.verdict === "FAIL" && "bg-red-500/10 text-red-400 border-red-500/20",
                    eval_item.verdict === "WARN" && "bg-amber-500/10 text-amber-400 border-amber-500/20",
                  )}
                >
                  <span
                    className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      eval_item.verdict === "PASS" && "bg-emerald-400",
                      eval_item.verdict === "FAIL" && "bg-red-400",
                      eval_item.verdict === "WARN" && "bg-amber-400",
                    )}
                  />
                  {eval_item.verdict}
                </span>
              </td>
              <td className="py-3 px-4">
                <span className="font-mono text-xs text-slate-300">
                  {eval_item.root_cause_code}
                </span>
                <span className="text-xs text-slate-500 ml-2">
                  {ROOT_CAUSE_LABELS[eval_item.root_cause_code] || ""}
                </span>
              </td>
              <td className="py-3 px-4 text-slate-400 text-xs">
                {timeAgo(eval_item.created_at)}
              </td>
              <td className="py-3 px-4">
                <Link
                  href={`/dashboard/evaluation/${eval_item.run_id}`}
                  className="text-emerald-400 hover:text-emerald-300 transition-colors"
                >
                  <ExternalLink size={14} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
