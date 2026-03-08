export const VERDICT_COLORS: Record<string, string> = {
  PASS: "emerald",
  FAIL: "red",
  WARN: "amber",
};

export const SEVERITY_ORDER = ["blocker", "critical", "major", "minor", "none"] as const;

export const SEVERITY_COLORS: Record<string, string> = {
  blocker: "bg-red-900 text-red-100",
  critical: "bg-red-600 text-white",
  major: "bg-amber-600 text-white",
  minor: "bg-slate-600 text-slate-200",
  none: "bg-emerald-600 text-white",
};

export const METRIC_LABELS: Record<string, string> = {
  precision_at_k: "Precision@K",
  recall_at_k: "Recall@K",
  mrr: "MRR",
  ndcg_at_k: "NDCG@K",
  hit_rate_at_k: "Hit Rate@K",
  context_coverage: "Context Coverage",
  faithfulness: "Faithfulness",
  answer_relevance: "Answer Relevance",
};

export const ROOT_CAUSE_LABELS: Record<string, string> = {
  PASS: "All checks passed",
  INPUT_INVALID: "Invalid input",
  NO_CONTEXT_PROVIDED: "No context provided",
  NO_RESPONSE_GENERATED: "No response generated",
  SHOULD_HAVE_REFUSED: "Should have refused",
  FALSE_REFUSAL: "False refusal",
  RETRIEVAL_MISS: "Retrieval miss",
  NO_RELEVANT_DOCS_RETRIEVED: "No relevant docs",
  EXCESSIVE_NOISE: "Excessive noise",
  EVIDENCE_NOT_USED: "Evidence not used",
  HALLUCINATION: "Hallucination",
  GENERATION_UNFAITHFUL: "Unfaithful generation",
  OFF_TOPIC_RESPONSE: "Off-topic response",
  CHUNK_BOUNDARY_BROKEN: "Chunk boundary broken",
  CHUNK_INCOHERENT: "Incoherent chunk",
  CHUNK_TOO_SPARSE: "Sparse chunk",
  CHUNK_TOO_DENSE: "Dense chunk",
};

export const LAYER_NAMES: Record<string, string> = {
  layer_a: "Retrieval (A)",
  layer_b: "Generation (B)",
  layer_c: "Claims (C)",
  layer_d: "Root Cause (D)",
  cascade: "Cascade",
};

export const CASCADE_STEPS = [
  { id: 1, label: "Input Validation", layer: "input" },
  { id: 2, label: "Answerability Check", layer: "layer_d0" },
  { id: 3, label: "Retrieval Quality", layer: "layer_a" },
  { id: 4, label: "Evidence Mapping", layer: "layer_c" },
  { id: 5, label: "Generation Quality", layer: "layer_b" },
  { id: 6, label: "Pass", layer: "cascade" },
] as const;
