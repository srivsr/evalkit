from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ContextChunk(BaseModel):
    """Rich context representation with rank and score for evaluation + AutoFix"""
    text: str
    source_id: Optional[str] = None
    rank: Optional[int] = None
    score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class CanonicalEvaluation(BaseModel):
    """
    Canonical format that ALL integrations normalize to.

    LangChain/LlamaIndex/Raw → CanonicalEvaluation → Evaluator

    CRITICAL: evaluator_version is first-class for cache invalidation
    CRITICAL: context_chunks order must be preserved (rank-sensitive)
    """
    # Core inputs
    query: str
    response: str
    context_chunks: List[ContextChunk]
    ground_truth: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    framework: Optional[str] = None  # langchain, llama_index, raw

    # Versioning (CRITICAL for cache invalidation)
    evaluator_version: str = "3"

    # Timings
    retrieval_latency_ms: Optional[int] = None
    generation_latency_ms: Optional[int] = None
    total_latency_ms: Optional[int] = None

    # Costs
    retrieval_cost: Optional[float] = None
    generation_cost: Optional[float] = None
    total_cost: Optional[float] = None

    # Configuration
    judge_model: str = "gpt-4o-mini"
    policy_version: int = 1

    # Identifiers
    project_id: Optional[str] = None
    evaluation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
