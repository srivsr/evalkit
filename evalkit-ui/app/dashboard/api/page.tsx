"use client";
import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks/useApi";
import { cn } from "@/lib/utils";
import type { ApiKeyItem } from "@/lib/types";
import { Copy, Check, Plus, Trash2, Key } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ENDPOINTS = [
  { method: "GET", path: "/v1/health", desc: "Health check", auth: false },
  { method: "POST", path: "/v1/projects", desc: "Create a project", auth: true },
  { method: "GET", path: "/v1/projects", desc: "List your projects", auth: true },
  { method: "GET", path: "/v1/projects/{id}", desc: "Get a project", auth: true },
  { method: "POST", path: "/v1/evaluate", desc: "Run evaluation pipeline", auth: true },
  { method: "GET", path: "/v1/evaluations?project_id={id}", desc: "List evaluations", auth: true },
  { method: "GET", path: "/v1/evaluations/{run_id}", desc: "Get evaluation result", auth: true },
  { method: "GET", path: "/v1/compare?run_a={id}&run_b={id}", desc: "Compare two runs", auth: true },
  { method: "POST", path: "/v1/evaluations/{run_id}/baseline", desc: "Mark as baseline", auth: true },
] as const;

function methodColor(method: string) {
  return {
    GET: "text-emerald-400 bg-emerald-400/10",
    POST: "text-blue-400 bg-blue-400/10",
    DELETE: "text-red-400 bg-red-400/10",
  }[method] || "text-slate-400 bg-slate-400/10";
}

export default function ApiPage() {
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = useCallback(() => api.apiKeys.list(), []);
  const { data: keys, refetch } = useApi<ApiKeyItem[]>(fetchKeys, []);

  async function handleCreate() {
    if (!newKeyName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const result = await api.apiKeys.create(newKeyName.trim());
      setCreatedKey(result.key);
      setNewKeyName("");
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create key");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(id: string) {
    try {
      await api.apiKeys.revoke(id);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke key");
    }
  }

  function handleCopy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-10">
      <h1 className="text-2xl font-bold">Developer API</h1>

      {/* API Keys Section */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Key size={18} /> API Keys
        </h2>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 text-sm text-red-400 mb-4">
            {error}
          </div>
        )}

        {/* Create Key Modal */}
        {createdKey && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-md p-4 mb-4">
            <p className="text-sm text-emerald-400 font-medium mb-2">
              Key created — copy it now. You won&apos;t see it again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-slate-900 px-3 py-2 rounded text-sm font-mono text-slate-200 break-all">
                {createdKey}
              </code>
              <button
                onClick={() => handleCopy(createdKey)}
                className="p-2 rounded hover:bg-slate-800 transition-colors"
              >
                {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
              </button>
            </div>
            <button
              onClick={() => setCreatedKey(null)}
              className="mt-2 text-xs text-slate-500 hover:text-slate-400"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Create Key Form */}
        <div className="flex items-center gap-3 mb-4">
          <input
            type="text"
            placeholder="Key name (e.g. CI Pipeline)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            className="bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-sm flex-1 max-w-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            onClick={handleCreate}
            disabled={!newKeyName.trim() || creating}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-md text-sm font-medium transition-colors"
          >
            <Plus size={14} />
            {creating ? "Creating..." : "Create Key"}
          </button>
        </div>

        {/* Keys Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-left">
                <th className="py-3 px-4 font-medium">Name</th>
                <th className="py-3 px-4 font-medium">Key</th>
                <th className="py-3 px-4 font-medium">Created</th>
                <th className="py-3 px-4 font-medium">Last Used</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {keys?.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No API keys yet. Create one to get started.
                  </td>
                </tr>
              )}
              {keys?.map((k) => (
                <tr key={k.id} className="border-b border-slate-800/50">
                  <td className="py-3 px-4 text-slate-300">{k.name}</td>
                  <td className="py-3 px-4 font-mono text-xs text-slate-500">{k.prefix}</td>
                  <td className="py-3 px-4 text-slate-500 text-xs">
                    {new Date(k.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-xs">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="py-3 px-4">
                    {k.revoked_at ? (
                      <span className="text-xs text-red-400">Revoked</span>
                    ) : (
                      <span className="text-xs text-emerald-400">Active</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {!k.revoked_at && (
                      <button
                        onClick={() => handleRevoke(k.id)}
                        className="p-1 rounded hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-colors"
                        title="Revoke key"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* API Endpoints Section */}
      <section>
        <h2 className="text-lg font-semibold mb-4">API Endpoints</h2>
        <p className="text-sm text-slate-400 mb-6">
          All authenticated endpoints accept an <code className="text-emerald-400">X-API-Key</code> header
          or a Bearer token.
        </p>

        <div className="space-y-3">
          {ENDPOINTS.map((ep) => (
            <div key={ep.method + ep.path} className="bg-slate-900 border border-slate-800 rounded-md p-4">
              <div className="flex items-center gap-3 mb-2">
                <span className={cn("px-2 py-0.5 rounded text-xs font-bold", methodColor(ep.method))}>
                  {ep.method}
                </span>
                <code className="text-sm text-slate-300">{ep.path}</code>
                <span className="text-xs text-slate-500 ml-auto">{ep.desc}</span>
              </div>
              <pre className="bg-slate-950 rounded p-3 text-xs text-slate-400 overflow-x-auto">
{`curl ${ep.auth ? '-H "X-API-Key: ek_YOUR_KEY" \\\n     ' : ""}${API_BASE}${ep.path.replace(/\{[^}]+\}/g, "EXAMPLE_ID")}`}
              </pre>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
