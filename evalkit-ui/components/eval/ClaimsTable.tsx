"use client";
import { cn } from "@/lib/utils";
import type { ClaimVerification } from "@/lib/types";

const supportStyles: Record<string, string> = {
  supported: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  partially_supported: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  unsupported: "bg-red-500/10 text-red-400 border-red-500/20",
};

const supportLabels: Record<string, string> = {
  supported: "Supported",
  partially_supported: "Partial",
  unsupported: "Unsupported",
};

export function ClaimsTable({ claims }: { claims: ClaimVerification }) {
  if (claims.claims.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No claims extracted from this response.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 mb-6">
        <div className="text-2xl font-mono font-bold">
          {(claims.supported_pct * 100).toFixed(0)}%
        </div>
        <div className="text-sm text-slate-400">claims supported</div>
        <div className="flex-1" />
        <div className="flex gap-2 text-xs">
          <span className="text-emerald-400">
            {claims.claims.filter((c) => c.support === "supported").length} supported
          </span>
          <span className="text-amber-400">
            {claims.claims.filter((c) => c.support === "partially_supported").length} partial
          </span>
          <span className="text-red-400">
            {claims.claims.filter((c) => c.support === "unsupported").length} unsupported
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 text-left">
              <th className="py-2 px-3 font-medium w-12">#</th>
              <th className="py-2 px-3 font-medium">Claim</th>
              <th className="py-2 px-3 font-medium w-32">Status</th>
              <th className="py-2 px-3 font-medium">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {claims.claims.map((claim, i) => (
              <tr
                key={claim.claim_id}
                className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
              >
                <td className="py-3 px-3 font-mono text-slate-500">{i + 1}</td>
                <td className="py-3 px-3">{claim.text}</td>
                <td className="py-3 px-3">
                  <span
                    className={cn(
                      "inline-flex px-2 py-0.5 rounded-full text-xs font-medium border",
                      supportStyles[claim.support] || "bg-slate-500/10 text-slate-400",
                    )}
                  >
                    {supportLabels[claim.support] || claim.support}
                  </span>
                </td>
                <td className="py-3 px-3 text-slate-400 text-xs font-mono">
                  {claim.evidence.length > 0
                    ? claim.evidence.map((e) => e.quote).join("; ")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
