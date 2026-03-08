"""EvalKit request models — from EVALKIT_MASTER_SPEC_v2.md Section 8."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TermPair(BaseModel):
    term_a: str = Field(..., max_length=1000)
    term_b: str = Field(..., max_length=1000)
    expected: Literal["similar", "dissimilar"] = "similar"


class EmbeddingFitnessRequest(BaseModel):
    project_id: str = Field(..., max_length=200)
    embedding_model: str = "text-embedding-3-small"
    domain: Optional[str] = Field(None, max_length=200)
    term_pairs: list[TermPair] = Field(..., min_length=1, max_length=200)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class ContextItem(BaseModel):
    id: str = Field(..., max_length=500)
    text: str = Field(..., max_length=100_000)
    source: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[dict] = None


class EvalConfig(BaseModel):
    k: int = 5
    judge_mode: Literal["single", "multi", "auto"] = "auto"
    judge_models: list[str] = Field(default_factory=lambda: ["gpt-4o"])
    cost_cap_usd: Optional[float] = None
    timeout_ms: int = 30000
    confidence_threshold: float = 0.75
    escalation_models: Optional[list[str]] = None
    relevance_labels: Optional[dict[str, float]] = None
    hallucination_tier: Literal["auto", "1", "2", "3"] = "auto"


class EvaluateRequest(BaseModel):
    project_id: str = Field(..., max_length=200)
    run_id: Optional[str] = Field(None, max_length=200)
    query: str = Field(..., max_length=50_000)
    response: str = Field(..., max_length=100_000)
    contexts: list[ContextItem]
    reference_answer: Optional[str] = Field(None, max_length=100_000)
    config: EvalConfig = Field(default_factory=EvalConfig)


class ChunkItem(BaseModel):
    id: str = Field(..., max_length=500)
    text: str = Field(..., max_length=100_000)
    source: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[dict] = None


class ChunkEvalRequest(BaseModel):
    chunks: list[ChunkItem]
    sample_size: int = Field(default=20, ge=1, le=1000)
    domain: Optional[str] = Field(None, max_length=200)


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
