"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChunkEvalResponse } from "@/lib/types";
import { SeverityPill } from "@/components/eval/SeverityPill";

const GOLDEN_FIXTURE = [
  { id: "chunk_1", text: "The patient was adm", source: "medical.pdf" },
  { id: "chunk_2", text: "itted to the ICU for monitoring.", source: "medical.pdf" },
  { id: "chunk_3", text: "Blood pressure was stable at 120/80. Heart rate normal.", source: "medical.pdf" },
];

const qualityColor: Record<string, string> = {
  good: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  fair: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  poor: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function ChunksPage() {
  const [chunksJson, setChunksJson] = useState("");
  const [sampleSize, setSampleSize] = useState("20");
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ChunkEvalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function loadFixture() {
    setChunksJson(JSON.stringify(GOLDEN_FIXTURE, null, 2));
    setSampleSize("20");
    setDomain("healthcare");
    setResult(null);
    setError(null);
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const chunks = JSON.parse(chunksJson);
      const res = await api.chunks.evaluate(
        chunks,
        sampleSize ? Number(sampleSize) : undefined,
        domain || undefined,
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-8">Chunk Quality Evaluation</h1>

      <div className="space-y-4 mb-8">
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs text-slate-500">Chunks (JSON array)</label>
            <button
              onClick={loadFixture}
              className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
            >
              Load Golden Fixture
            </button>
          </div>
          <textarea
            value={chunksJson}
            onChange={(e) => setChunksJson(e.target.value)}
            rows={10}
            placeholder='[{"id": "chunk_1", "text": "...", "source": "file.pdf"}]'
            className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500 resize-y"
          />
        </div>

        <div className="flex gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Sample Size</label>
            <input
              type="number"
              value={sampleSize}
              onChange={(e) => setSampleSize(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-sm w-32 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Domain</label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="e.g. healthcare"
              className="bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleSubmit}
              disabled={!chunksJson.trim() || loading}
              className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-md text-sm font-medium transition-colors"
            >
              {loading ? "Evaluating..." : "Evaluate Chunks"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 text-sm text-red-400 mb-6">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <span
              className={cn(
                "px-3 py-1 rounded-full text-sm font-medium border",
                qualityColor[result.overall_quality] || "text-slate-400",
              )}
            >
              {result.overall_quality.toUpperCase()}
            </span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Score</span>
                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      result.score >= 0.7 ? "bg-emerald-500" : result.score >= 0.4 ? "bg-amber-500" : "bg-red-500",
                    )}
                    style={{ width: `${(result.score * 100).toFixed(0)}%` }}
                  />
                </div>
                <span className="text-sm font-mono text-slate-300">{(result.score * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Total Chunks", value: result.summary.total_chunks },
              { label: "Issues Found", value: result.summary.issues_found },
              { label: "Boundary Issues", value: result.summary.boundary_issues },
              { label: "Avg Chunk Size", value: `${result.summary.avg_chunk_size} chars` },
            ].map((stat) => (
              <div key={stat.label} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">{stat.label}</div>
                <div className="text-lg font-bold">{stat.value}</div>
              </div>
            ))}
          </div>

          {result.issues.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Issues</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-left">
                      <th className="py-3 px-4 font-medium">Chunk</th>
                      <th className="py-3 px-4 font-medium">Issue</th>
                      <th className="py-3 px-4 font-medium">Severity</th>
                      <th className="py-3 px-4 font-medium">Detail</th>
                      <th className="py-3 px-4 font-medium">Fix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.issues.map((issue, i) => (
                      <tr key={i} className="border-b border-slate-800/50">
                        <td className="py-3 px-4 font-mono text-slate-300">{issue.chunk_id}</td>
                        <td className="py-3 px-4 text-slate-300">{issue.issue}</td>
                        <td className="py-3 px-4"><SeverityPill severity={issue.severity} /></td>
                        <td className="py-3 px-4 text-slate-400 text-xs max-w-xs">{issue.detail}</td>
                        <td className="py-3 px-4 text-emerald-400 text-xs max-w-xs">{issue.fix}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {!result && !error && (
        <div className="text-center py-16 text-slate-500">
          <p className="text-lg mb-2">Evaluate your chunk quality</p>
          <p className="text-sm">Paste a JSON array of chunks or load the golden fixture to test boundary detection.</p>
        </div>
      )}
    </div>
  );
}
