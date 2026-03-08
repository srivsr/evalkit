"use client";
import { useState, useMemo } from "react";
import { useApi } from "@/lib/hooks/useApi";
import { api } from "@/lib/api";
import { formatScore, cn } from "@/lib/utils";
import { METRIC_LABELS } from "@/lib/constants";
import type { EvaluationListItem, CompareResponse } from "@/lib/types";
import { ProjectSelector } from "@/components/dashboard/ProjectSelector";
import { MetricChart } from "@/components/eval/MetricChart";

export default function ComparePage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [runA, setRunA] = useState("");
  const [runB, setRunB] = useState("");
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: evaluations } = useApi<EvaluationListItem[]>(
    () => (projectId ? api.evaluations.list(projectId) : Promise.resolve([])),
    [projectId],
  );

  async function handleCompare() {
    if (!runA || !runB) return;
    setComparing(true);
    setError(null);
    try {
      const res = await api.compare(runA, runB);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setComparing(false);
    }
  }

  const chartData = useMemo(() => {
    if (!result) return [];
    return result.deltas
      .filter((d) => d.run_a_value !== null && d.run_b_value !== null)
      .map((d) => ({
        name: METRIC_LABELS[d.metric] || d.metric,
        "Run A": d.run_a_value as number,
        "Run B": d.run_b_value as number,
      }));
  }, [result]);

  const verdictLabel = result
    ? { improved: "Improved", stable: "Stable", degraded: "Degraded" }[result.verdict]
    : "";
  const verdictStyle = result
    ? { improved: "text-emerald-400", stable: "text-slate-400", degraded: "text-red-400" }[result.verdict]
    : "";

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-8">Compare Runs</h1>

      <div className="flex items-end gap-4 mb-8 flex-wrap">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Project</label>
          <ProjectSelector selectedId={projectId} onSelect={(id) => { setProjectId(id); setRunA(""); setRunB(""); setResult(null); }} />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Run A (Baseline)</label>
          <select
            value={runA}
            onChange={(e) => setRunA(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-sm min-w-[200px] focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="">Select run...</option>
            {evaluations?.map((e) => (
              <option key={e.run_id} value={e.run_id}>
                {e.run_id.substring(0, 12)} ({e.verdict})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Run B (Current)</label>
          <select
            value={runB}
            onChange={(e) => setRunB(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-sm min-w-[200px] focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="">Select run...</option>
            {evaluations?.map((e) => (
              <option key={e.run_id} value={e.run_id}>
                {e.run_id.substring(0, 12)} ({e.verdict})
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleCompare}
          disabled={!runA || !runB || runA === runB || comparing}
          className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-md text-sm font-medium transition-colors"
        >
          {comparing ? "Comparing..." : "Compare"}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 text-sm text-red-400 mb-6">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-8">
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400">Overall:</span>
            <span className={cn("text-lg font-bold", verdictStyle)}>{verdictLabel}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-left">
                  <th className="py-3 px-4 font-medium">Metric</th>
                  <th className="py-3 px-4 font-medium text-right">Run A</th>
                  <th className="py-3 px-4 font-medium text-right">Run B</th>
                  <th className="py-3 px-4 font-medium text-right">Delta</th>
                  <th className="py-3 px-4 font-medium text-right">Delta %</th>
                </tr>
              </thead>
              <tbody>
                {result.deltas.map((d) => {
                  const isRegression = result.regressions.some((r) => r.metric === d.metric);
                  return (
                    <tr
                      key={d.metric}
                      className={cn(
                        "border-b border-slate-800/50",
                        isRegression && "bg-red-500/5",
                      )}
                    >
                      <td className="py-3 px-4 text-slate-300">
                        {METRIC_LABELS[d.metric] || d.metric}
                        {isRegression && (
                          <span className="ml-2 text-xs text-red-400 font-medium">REGRESSION</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-slate-300">
                        {formatScore(d.run_a_value)}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-slate-300">
                        {formatScore(d.run_b_value)}
                      </td>
                      <td className={cn(
                        "py-3 px-4 text-right font-mono",
                        d.delta !== null && d.delta > 0 ? "text-emerald-400" : d.delta !== null && d.delta < 0 ? "text-red-400" : "text-slate-500",
                      )}>
                        {d.delta !== null ? (d.delta > 0 ? "+" : "") + formatScore(d.delta) : "N/A"}
                      </td>
                      <td className={cn(
                        "py-3 px-4 text-right font-mono text-xs",
                        d.delta_pct !== null && d.delta_pct > 0 ? "text-emerald-400" : d.delta_pct !== null && d.delta_pct < 0 ? "text-red-400" : "text-slate-500",
                      )}>
                        {d.delta_pct !== null ? (d.delta_pct > 0 ? "+" : "") + d.delta_pct.toFixed(1) + "%" : "N/A"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {chartData.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Side-by-Side</h3>
              <CompareChart data={chartData} />
            </div>
          )}
        </div>
      )}

      {!result && !error && (
        <div className="text-center py-16 text-slate-500">
          <p className="text-lg mb-2">Select two runs to compare</p>
          <p className="text-sm">Pick a project and two evaluation runs to see metric deltas and regressions.</p>
        </div>
      )}
    </div>
  );
}

function CompareChart({ data }: { data: { name: string; "Run A": number; "Run B": number }[] }) {
  // Lazy import recharts to keep SSR working
  const { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } = require("recharts");

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} domain={[0, 1]} />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "8px" }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <Legend wrapperStyle={{ color: "#94a3b8" }} />
          <Bar dataKey="Run A" fill="#6366f1" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Run B" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
