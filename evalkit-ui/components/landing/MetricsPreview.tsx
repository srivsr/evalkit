import Link from "next/link";
import { ArrowRight } from "lucide-react";

const sampleResult = {
  verdict: "PASS",
  overall_score: 1.0,
  root_cause: { code: "PASS", severity: "none", message: "All checks passed" },
  retrieval: { precision_at_k: 1.0, recall_at_k: 1.0, mrr: 1.0, ndcg_at_k: 1.0, hit_rate_at_k: 1.0 },
  claims: { supported_pct: 1.0, total: 1, supported: 1 },
  telemetry: { total_latency_ms: 12, estimated_cost_usd: 0 },
};

export function MetricsPreview() {
  return (
    <section className="py-20 px-4 max-w-5xl mx-auto">
      <h2 className="text-3xl font-bold text-center mb-4">Sample Evaluation</h2>
      <p className="text-slate-400 text-center mb-10">
        &quot;What is the capital of France?&quot; evaluated against retrieved context.
      </p>

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            PASS
          </span>
          <span className="font-mono text-slate-400 text-sm">
            Score: {sampleResult.overall_score.toFixed(2)}
          </span>
          <span className="font-mono text-slate-500 text-sm">
            {sampleResult.telemetry.total_latency_ms}ms | Free
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {Object.entries(sampleResult.retrieval).map(([key, val]) => (
            <div key={key} className="text-center">
              <div className="text-lg font-mono font-bold text-emerald-400">
                {val.toFixed(2)}
              </div>
              <div className="text-xs text-slate-500">
                {key.replace(/_at_k/g, "@K").replace(/_/g, " ").toUpperCase()}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <div className="text-sm text-slate-400">
            Claims: {sampleResult.claims.supported}/{sampleResult.claims.total} supported ({(sampleResult.claims.supported_pct * 100).toFixed(0)}%)
          </div>
          <div className="text-sm">
            <span className="font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
              {sampleResult.root_cause.code}
            </span>
          </div>
        </div>
      </div>

      <div className="text-center mt-10">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-emerald-400 hover:text-emerald-300 transition-colors"
        >
          Try the Dashboard <ArrowRight size={16} />
        </Link>
      </div>
    </section>
  );
}
