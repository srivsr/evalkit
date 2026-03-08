export type Verdict = "PASS" | "FAIL" | "WARN";
export type Severity = "blocker" | "critical" | "major" | "minor" | "none";
export type AnswerabilityClass = "answerable" | "partially_answerable" | "unanswerable";
export type SupportStatus = "supported" | "partially_supported" | "unsupported";

export interface Project {
  id: string;
  name: string;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  db_connected: boolean;
}

export interface ContextItem {
  id: string;
  text: string;
  source?: string;
  metadata?: Record<string, unknown>;
}

export interface EvalConfig {
  k?: number;
  judge_mode?: "single" | "multi";
  judge_models?: string[];
  relevance_labels?: Record<string, number>;
  timeout_ms?: number;
  cost_cap_usd?: number;
}

export interface EvaluateRequest {
  project_id: string;
  query: string;
  response: string;
  contexts: ContextItem[];
  reference_answer?: string;
  config?: EvalConfig;
}

export interface ConfidenceInfo {
  mode: string;
  judge_count: number;
  agreement_pct?: number | null;
}

export interface Summary {
  verdict: Verdict;
  confidence: ConfidenceInfo;
  overall_score: number;
}

export interface Answerability {
  classification: AnswerabilityClass;
  rationale: string;
  expected_behavior: string;
}

export interface RetrievalMetrics {
  precision_at_k: number | null;
  recall_at_k: number | null;
  mrr: number | null;
  ndcg_at_k: number | null;
  hit_rate_at_k: number | null;
  context_coverage: number | null;
  k: number;
}

export interface GenerationScores {
  faithfulness: number | null;
  answer_relevance: number | null;
}

export interface GenerationMetrics {
  scores: GenerationScores;
  judge_model: string | null;
  prompt_version?: string | null;
}

export interface EvidenceSpan {
  context_id: string;
  span_start: number;
  span_end: number;
  quote: string;
}

export interface Claim {
  claim_id: string;
  text: string;
  support: SupportStatus;
  evidence: EvidenceSpan[];
}

export interface ClaimVerification {
  claims: Claim[];
  supported_pct: number;
  unsupported_claims: string[];
}

export interface RootCause {
  code: string;
  message: string;
  severity: Severity;
  attribution: string;
}

export interface Anomaly {
  code: string;
  severity: string;
  message: string;
}

export interface FixSuggestion {
  target: string;
  action: string;
  priority: "high" | "medium" | "low";
  detail?: string;
}

export interface Telemetry {
  total_latency_ms: number;
  layer_a_ms: number;
  layer_b_ms: number;
  layer_c_ms: number;
  estimated_cost_usd: number;
  tokens_used: number;
}

export interface EvalInput {
  query: string;
  response: string;
  contexts: ContextItem[];
  reference_answer?: string | null;
  config?: EvalConfig | null;
}

export interface EvaluateResponse {
  project_id: string;
  run_id: string;
  created_at: string;
  summary: Summary;
  answerability: Answerability;
  layer_a_retrieval: RetrievalMetrics;
  layer_b_generation: GenerationMetrics;
  layer_c_claims: ClaimVerification;
  root_cause: RootCause;
  secondary_root_cause?: RootCause | null;
  anomalies: Anomaly[];
  fix_suggestions: FixSuggestion[];
  telemetry: Telemetry;
  input?: EvalInput;
}

export interface MetricDelta {
  metric: string;
  run_a_value: number | null;
  run_b_value: number | null;
  delta: number | null;
  delta_pct: number | null;
}

export interface CompareResponse {
  run_a: string;
  run_b: string;
  deltas: MetricDelta[];
  regressions: MetricDelta[];
  verdict: "improved" | "stable" | "degraded";
}

export interface EvaluationListItem {
  run_id: string;
  project_id: string;
  verdict: string;
  root_cause_code: string;
  created_at: string;
}

export interface LegalDocument {
  title: string;
  slug: string;
  content: string;
  effective_date: string;
  last_updated: string;
}

export interface CreateOrderResponse {
  order_id: string;
  approval_url: string | null;
  provider: string;
  tier: string;
  amount_usd: number;
}

export interface ApiKeyItem {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface ApiKeyCreated extends ApiKeyItem {
  key: string;
}

export interface ChunkIssue {
  chunk_id: string;
  issue: string;
  severity: Severity;
  detail: string;
  fix: string;
}

export interface ChunkEvalSummary {
  total_chunks: number;
  issues_found: number;
  boundary_issues: number;
  avg_chunk_size: number;
}

export interface ChunkEvalResponse {
  overall_quality: "good" | "fair" | "poor";
  score: number;
  summary: ChunkEvalSummary;
  issues: ChunkIssue[];
}
