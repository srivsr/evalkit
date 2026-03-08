"""EvalKit response models — from EVALKIT_MASTER_SPEC_v2.md Section 8."""
from typing import Optional
from pydantic import BaseModel, Field

from evalkit.models.enums import (
    Verdict, Severity, RootCauseCode, AnswerabilityClass, ChunkQuality
)


# --- Sub-models for EvaluateResponse ---

class ConfidenceInfo(BaseModel):
    mode: str = "single_judge"  # single_judge | multi_judge | auto_*
    judge_count: int = 1
    agreement_pct: Optional[float] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None

class Summary(BaseModel):
    verdict: Verdict
    confidence: ConfidenceInfo
    overall_score: float  # 0.0-1.0

class Answerability(BaseModel):
    classification: AnswerabilityClass
    rationale: str
    expected_behavior: str

class RetrievalMetrics(BaseModel):
    precision_at_k: Optional[float] = None
    recall_at_k: Optional[float] = None
    mrr: Optional[float] = None
    ndcg_at_k: Optional[float] = None
    hit_rate_at_k: Optional[float] = None
    context_coverage: Optional[float] = None
    k: int = 5

class GenerationScores(BaseModel):
    faithfulness: Optional[float] = None
    answer_relevance: Optional[float] = None

class GenerationMetrics(BaseModel):
    scores: GenerationScores
    judge_model: Optional[str] = None
    prompt_version: Optional[str] = None

class EvidenceSpan(BaseModel):
    context_id: str
    span_start: int
    span_end: int
    quote: str

class Claim(BaseModel):
    claim_id: str
    text: str
    support: str  # supported | partially_supported | unsupported
    evidence: list[EvidenceSpan] = Field(default_factory=list)

class ClaimVerification(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    supported_pct: float = 0.0
    unsupported_claims: list[str] = Field(default_factory=list)

class RootCause(BaseModel):
    code: RootCauseCode
    message: str
    severity: Severity
    attribution: str  # Which layer identified this

class Anomaly(BaseModel):
    code: str
    severity: str
    message: str

class FixSuggestion(BaseModel):
    target: str  # retrieval | generation | chunking | indexing
    action: str
    priority: str  # high | medium | low
    detail: Optional[str] = None

class Telemetry(BaseModel):
    total_latency_ms: int = 0
    layer_a_ms: int = 0
    layer_b_ms: int = 0
    layer_c_ms: int = 0
    estimated_cost_usd: float = 0.0
    tokens_used: int = 0


class HallucinationDetail(BaseModel):
    entity_errors: list[str] = Field(default_factory=list)
    number_errors: list[str] = Field(default_factory=list)
    logic_errors: list[str] = Field(default_factory=list)
    temporal_errors: list[str] = Field(default_factory=list)


class HallucinationTierResult(BaseModel):
    tier_used: int
    score: float
    confidence: float
    confidence_interval: list[float]
    method: str
    detail: Optional[HallucinationDetail] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None


# --- Main Response Models ---

class EvaluateResponse(BaseModel):
    project_id: str
    run_id: str
    created_at: str  # ISO format

    summary: Summary
    answerability: Answerability
    layer_a_retrieval: RetrievalMetrics
    layer_b_generation: GenerationMetrics
    layer_c_claims: ClaimVerification
    root_cause: RootCause
    secondary_root_cause: Optional[RootCause] = None
    hallucination_tier: Optional[HallucinationTierResult] = None
    anomalies: list[Anomaly] = Field(default_factory=list)
    fix_suggestions: list[FixSuggestion] = Field(default_factory=list)
    telemetry: Telemetry


# --- Chunk Evaluation Response ---

class ChunkIssue(BaseModel):
    chunk_id: str
    issue: str
    detail: str
    severity: str
    fix: str

class ChunkEvalSummary(BaseModel):
    chunks_evaluated: int
    boundary_issues: int
    coherence_issues: int
    density_issues: int

class ChunkEvalResponse(BaseModel):
    overall_quality: ChunkQuality
    score: float
    issues: list[ChunkIssue] = Field(default_factory=list)
    summary: ChunkEvalSummary


# --- Project Response ---

class ProjectResponse(BaseModel):
    id: str
    name: str
    created_at: str


# --- Compare Response ---

class MetricDelta(BaseModel):
    metric: str
    run_a_value: Optional[float]
    run_b_value: Optional[float]
    delta: Optional[float]
    delta_pct: Optional[float]

class CompareResponse(BaseModel):
    run_a: str
    run_b: str
    deltas: list[MetricDelta] = Field(default_factory=list)
    regressions: list[MetricDelta] = Field(default_factory=list)
    verdict: str  # "improved" | "degraded" | "stable"


# --- Embedding Fitness Response ---

class TermPairResult(BaseModel):
    term_a: str
    term_b: str
    expected: str
    similarity: float
    passed: bool


class EmbeddingFitnessResponse(BaseModel):
    project_id: str
    embedding_model: str
    domain: Optional[str]
    fitness_score: float
    total_pairs: int
    passed_pairs: int
    failed_pairs: int
    results: list[TermPairResult]
    recommendations: list[str]
    root_cause: Optional[str] = None


# --- Error Response ---

class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: Optional[str] = None


# --- Health Response ---

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    db_connected: bool = True


