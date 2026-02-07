from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from .canonical import ContextChunk


class EvaluateRequest(BaseModel):
    """API request for POST /v1/evaluate"""
    project_id: UUID
    query: str
    response: str

    # Support both simple and rich context formats
    context: Optional[List[str]] = None
    context_chunks: Optional[List[ContextChunk]] = None

    ground_truth: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchEvaluateRequest(BaseModel):
    """Batch evaluation request"""
    project_id: UUID
    evaluations: List[Dict[str, Any]]
