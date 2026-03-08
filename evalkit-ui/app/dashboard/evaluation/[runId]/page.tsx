"use client";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useApi } from "@/lib/hooks/useApi";
import { api } from "@/lib/api";
import { formatScore, formatLatency, formatCost, verdictColor, cn } from "@/lib/utils";
import { METRIC_LABELS } from "@/lib/constants";
import type { EvaluateResponse } from "@/lib/types";
import { VerdictBadge } from "@/components/eval/VerdictBadge";
import { MetricBar } from "@/components/eval/MetricBar";
import { MetricChart } from "@/components/eval/MetricChart";
import { ClaimsTable } from "@/components/eval/ClaimsTable";
import { RootCauseCard } from "@/components/eval/RootCauseCard";
import { CascadeViz } from "@/components/eval/CascadeViz";
import { FixSuggestions } from "@/components/eval/FixSuggestions";
import { AnomalyAlerts } from "@/components/eval/AnomalyAlerts";

export default function EvaluationDetailPage() {
  const params = useParams();
  const runId = params.runId as string;

  const { data: evaluation, loading, error } = useApi<EvaluateResponse>(
    () => api.evaluations.get(runId),
    [runId],
  );

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="inline-block w-6 h-6 border-2 border-slate-600 border-t-emerald-400 rounded-full animate-spin" />
        <p className="mt-3 text-sm text-slate-500">Loading evaluation...</p>
      </div>
    );
  }

  if (error || !evaluation) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/20 rounded-md p-4 text-red-400">
          {error || "Evaluation not found"}
        </div>
      </div>
    );
  }

  const retrieval = evaluation.layer_a_retrieval;
  const generation = evaluation.layer_b_generation;
  const claims = evaluation.layer_c_claims;
  const telemetry = evaluation.telemetry;

  const retrievalMetrics = [
    { label: METRIC_LABELS.precision_at_k, value: retrieval.precision_at_k },
    { label: METRIC_LABELS.recall_at_k, value: retrieval.recall_at_k },
    { label: METRIC_LABELS.mrr, value: retrieval.mrr },
    { label: METRIC_LABELS.ndcg_at_k, value: retrieval.ndcg_at_k },
    { label: METRIC_LABELS.hit_rate_at_k, value: retrieval.hit_rate_at_k },
    { label: METRIC_LABELS.context_coverage, value: retrieval.context_coverage },
  ];

  const generationMetrics = [
    { label: METRIC_LABELS.faithfulness, value: generation.scores.faithfulness },
    { label: METRIC_LABELS.answer_relevance, value: generation.scores.answer_relevance },
  ];

  const chartData = [
    ...retrievalMetrics.filter((m) => m.value !== null).map((m) => ({ name: m.label, value: m.value as number })),
    ...generationMetrics.filter((m) => m.value !== null).map((m) => ({ name: m.label, value: m.value as number })),
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-4"
        >
          <ArrowLeft size={14} /> Back to evaluations
        </Link>
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Evaluation Detail</h1>
          <VerdictBadge verdict={evaluation.summary.verdict} size="lg" />
        </div>
        <p className="text-sm text-slate-500 font-mono mt-1">{runId}</p>
      </div>

      <Tabs defaultValue="input">
        <TabsList className="mb-6">
          <TabsTrigger value="input">Input</TabsTrigger>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="claims">Claims</TabsTrigger>
          <TabsTrigger value="rootcause">Root Cause & Fixes</TabsTrigger>
        </TabsList>

        <TabsContent value="input">
          {evaluation.input ? (
            <div className="space-y-6">
              <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Query</h3>
                <p className="text-sm text-slate-200 whitespace-pre-wrap">{evaluation.input.query}</p>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Response</h3>
                <p className="text-sm text-slate-200 whitespace-pre-wrap">{evaluation.input.response}</p>
              </div>

              {evaluation.input.reference_answer && (
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">Reference Answer</h3>
                  <p className="text-sm text-slate-200 whitespace-pre-wrap">{evaluation.input.reference_answer}</p>
                </div>
              )}

              {evaluation.input.contexts.length > 0 && (
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                  <h3 className="text-sm font-medium text-slate-400 mb-3">Contexts ({evaluation.input.contexts.length})</h3>
                  <div className="space-y-3">
                    {evaluation.input.contexts.map((ctx, i) => (
                      <div key={ctx.id || i} className="rounded border border-slate-700 bg-slate-800/50 p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-slate-500">{ctx.id}</span>
                          {ctx.source && <span className="text-xs text-slate-500">| {ctx.source}</span>}
                        </div>
                        <p className="text-sm text-slate-300 whitespace-pre-wrap">{ctx.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {evaluation.input.config && (
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">Config</h3>
                  <pre className="text-xs text-slate-300 font-mono overflow-x-auto">{JSON.stringify(evaluation.input.config, null, 2)}</pre>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Input data not available for this evaluation.</p>
          )}
        </TabsContent>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Verdict" value={evaluation.summary.verdict} valueClass={verdictColor(evaluation.summary.verdict)} />
            <StatCard label="Overall Score" value={formatScore(evaluation.summary.overall_score)} />
            <StatCard label="Answerability" value={evaluation.answerability.classification} />
            <StatCard label="Confidence" value={`${evaluation.summary.confidence.mode} (${evaluation.summary.confidence.judge_count})`} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <StatCard label="Total Latency" value={formatLatency(telemetry.total_latency_ms)} />
            <StatCard label="Estimated Cost" value={formatCost(telemetry.estimated_cost_usd)} />
            <StatCard label="Tokens Used" value={telemetry.tokens_used.toLocaleString()} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard label="Layer A (Retrieval)" value={formatLatency(telemetry.layer_a_ms)} />
            <StatCard label="Layer B (Generation)" value={formatLatency(telemetry.layer_b_ms)} />
            <StatCard label="Layer C (Claims)" value={formatLatency(telemetry.layer_c_ms)} />
          </div>

          {evaluation.answerability.rationale && (
            <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
              <h3 className="text-sm font-medium text-slate-400 mb-2">Answerability Rationale</h3>
              <p className="text-sm text-slate-300">{evaluation.answerability.rationale}</p>
              <p className="text-xs text-slate-500 mt-2">{evaluation.answerability.expected_behavior}</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="metrics">
          <div className="space-y-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">Retrieval Metrics (Layer A)</h3>
              <div className="space-y-3">
                {retrievalMetrics.map((m) => (
                  <MetricBar key={m.label} label={m.label} value={m.value} />
                ))}
              </div>
              <p className="text-xs text-slate-500 mt-2">K = {retrieval.k}</p>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-4">Generation Metrics (Layer B)</h3>
              <div className="space-y-3">
                {generationMetrics.map((m) => (
                  <MetricBar key={m.label} label={m.label} value={m.value} />
                ))}
              </div>
              {generation.judge_model && (
                <p className="text-xs text-slate-500 mt-2">Judge: {generation.judge_model}</p>
              )}
              {generation.prompt_version && (
                <p className="text-xs text-slate-500">Prompt: v{generation.prompt_version}</p>
              )}
            </div>

            {chartData.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-4">All Metrics</h3>
                <MetricChart data={chartData} />
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="claims">
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <h3 className="text-lg font-semibold">Claim Verification (Layer C)</h3>
              <span className="text-sm text-slate-400">
                {formatScore(claims.supported_pct)}% supported
              </span>
            </div>
            <ClaimsTable claims={claims} />
            {claims.unsupported_claims.length > 0 && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
                <h4 className="text-sm font-medium text-red-400 mb-2">Unsupported Claims</h4>
                <ul className="space-y-1 text-sm text-slate-300">
                  {claims.unsupported_claims.map((id) => (
                    <li key={id} className="font-mono text-xs">{id}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="rootcause">
          <div className="space-y-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">Root Cause</h3>
              <div className="space-y-4">
                <RootCauseCard rootCause={evaluation.root_cause} label={evaluation.secondary_root_cause ? "Primary" : undefined} />
                {evaluation.secondary_root_cause && (
                  <RootCauseCard rootCause={evaluation.secondary_root_cause} label="Secondary" />
                )}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-4">Evaluation Cascade</h3>
              <CascadeViz rootCauseCode={evaluation.root_cause.code} attribution={evaluation.root_cause.attribution} />
            </div>

            {evaluation.fix_suggestions.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Fix Suggestions</h3>
                <FixSuggestions suggestions={evaluation.fix_suggestions} />
              </div>
            )}

            {evaluation.anomalies.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Anomalies</h3>
                <AnomalyAlerts anomalies={evaluation.anomalies} />
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatCard({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={cn("text-lg font-semibold font-mono", valueClass || "text-slate-100")}>{value}</p>
    </div>
  );
}
