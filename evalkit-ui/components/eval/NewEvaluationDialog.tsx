"use client";
import { useState } from "react";
import { X } from "lucide-react";
import { api } from "@/lib/api";

interface NewEvaluationDialogProps {
  projectId: string;
  open: boolean;
  onClose: () => void;
  onSuccess: (runId: string) => void;
}

export function NewEvaluationDialog({
  projectId,
  open,
  onClose,
  onSuccess,
}: NewEvaluationDialogProps) {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [contextsJson, setContextsJson] = useState('[\n  {"id": "ctx_1", "text": ""}\n]');
  const [k, setK] = useState(5);
  const [referenceAnswer, setReferenceAnswer] = useState("");
  const [relevanceLabelsJson, setRelevanceLabelsJson] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const contexts = JSON.parse(contextsJson);
      if (!Array.isArray(contexts)) throw new Error("Contexts must be a JSON array");

      const relevanceLabels = relevanceLabelsJson.trim()
        ? JSON.parse(relevanceLabelsJson)
        : undefined;

      const result = await api.evaluations.create({
        project_id: projectId,
        query,
        response,
        contexts,
        reference_answer: referenceAnswer || undefined,
        config: {
          k,
          ...(relevanceLabels && { relevance_labels: relevanceLabels }),
        },
      });
      onSuccess(result.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-slate-900 border border-slate-700 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">New Evaluation</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Query</label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 min-h-[60px]"
              placeholder="What is the capital of France?"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Response</label>
            <textarea
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 min-h-[60px]"
              placeholder="The capital of France is Paris."
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Contexts (JSON Array)
            </label>
            <textarea
              value={contextsJson}
              onChange={(e) => setContextsJson(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/50 min-h-[100px]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Reference Answer <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <textarea
              value={referenceAnswer}
              onChange={(e) => setReferenceAnswer(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 min-h-[50px]"
              placeholder="Expected correct answer for comparison"
            />
          </div>

          <div className="flex gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">K</label>
              <input
                type="number"
                value={k}
                onChange={(e) => setK(parseInt(e.target.value) || 5)}
                className="w-20 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                min={1}
                max={100}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Relevance Labels <span className="text-slate-500 font-normal">(optional JSON — maps context IDs to relevance scores)</span>
            </label>
            <textarea
              value={relevanceLabelsJson}
              onChange={(e) => setRelevanceLabelsJson(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500/50 min-h-[50px]"
              placeholder='{"ctx_1": 1.0, "ctx_2": 0.0}'
            />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !query || !response}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-md text-sm font-medium transition-colors"
            >
              {loading ? "Evaluating..." : "Run Evaluation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
