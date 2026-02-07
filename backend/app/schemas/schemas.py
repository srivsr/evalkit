from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal


class ContextChunk(BaseModel):
    text: str
    source_id: Optional[str] = None
    rank: Optional[int] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class CanonicalEvaluation(BaseModel):
    query: str
    response: str
    context_chunks: List[ContextChunk]
    ground_truth: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    evaluator_version: str = "3"
    retrieval_latency_ms: Optional[int] = None
    generation_latency_ms: Optional[int] = None
    total_latency_ms: Optional[int] = None


class EvaluateRequest(BaseModel):
    project_id: UUID
    query: str
    response: str
    context: Optional[List[str]] = None
    context_chunks: Optional[List[ContextChunk]] = None
    ground_truth: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    faithfulness: Optional[Decimal] = None
    answer_relevancy: Optional[Decimal] = None
    context_precision: Optional[Decimal] = None
    context_recall: Optional[Decimal] = None
    hallucination_score: Optional[Decimal] = None
    response_latency_ms: Optional[int] = None
    cost_per_query: Optional[Decimal] = None


class EvaluateResponse(BaseModel):
    evaluation_id: UUID
    metrics: MetricsResponse
    decision: str
    severity: Optional[str] = None
    failure_codes: List[str] = Field(default_factory=list)
    pipeline_stage: str
    cached: bool
    cost: Decimal
    duration_ms: int
    tokens_used: int
    autofix_available: bool


class AutofixRecommendationResponse(BaseModel):
    id: UUID
    rule_name: str
    type: str
    current_value: Any
    recommended_value: Any
    expected_improvement: str
    confidence: str
    evidence: Dict[str, Any]
    explanation: str


class AutofixResponse(BaseModel):
    evaluation_id: UUID
    recommendations: List[AutofixRecommendationResponse]


class BatchEvaluateRequest(BaseModel):
    project_id: UUID
    evaluations: List[Dict[str, Any]]


class BatchEvaluateResponse(BaseModel):
    batch_id: str
    status: str
    total_count: int
    estimated_completion_seconds: int


class AnalyticsResponse(BaseModel):
    period: str
    total_evaluations: int
    average_metrics: MetricsResponse
    decision_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    total_cost: Decimal
    cost_savings: Dict[str, Any]
    trends: Dict[str, List]
    top_failure_codes: List[Dict[str, Any]]
