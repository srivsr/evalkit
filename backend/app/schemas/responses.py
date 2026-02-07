from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal


class MetricsResponse(BaseModel):
    """Evaluation metrics response"""
    faithfulness: Optional[Decimal] = None
    answer_relevancy: Optional[Decimal] = None
    context_precision: Optional[Decimal] = None
    context_recall: Optional[Decimal] = None
    hallucination_score: Optional[Decimal] = None
    response_latency_ms: Optional[int] = None
    cost_per_query: Optional[Decimal] = None


class EvaluateResponse(BaseModel):
    """API response for POST /v1/evaluate"""
    evaluation_id: UUID
    metrics: MetricsResponse
    decision: str  # pass, fail, warn
    severity: Optional[str] = None  # P0, P1, P2, P3
    failure_codes: List[str] = []
    pipeline_stage: str  # deterministic, small_model, large_model
    cached: bool
    cost: Decimal
    duration_ms: int
    tokens_used: int
    autofix_available: bool


class BatchEvaluateResponse(BaseModel):
    """Batch evaluation response"""
    batch_id: str
    status: str
    total_count: int
    estimated_completion_seconds: int


class AutofixRecommendationResponse(BaseModel):
    """Single AutoFix recommendation"""
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
    """AutoFix recommendations response"""
    evaluation_id: UUID
    recommendations: List[AutofixRecommendationResponse]
