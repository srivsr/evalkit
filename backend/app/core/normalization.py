from typing import Dict, List, Any
from ..schemas.canonical import CanonicalEvaluation, ContextChunk
from ..schemas.requests import EvaluateRequest


def normalize_api_request(request: EvaluateRequest) -> CanonicalEvaluation:
    """
    Convert API request to canonical format.

    Supports both:
    - context: List[str] (simple format)
    - context_chunks: List[ContextChunk] (rich format with rank/score)
    """
    if request.context_chunks:
        chunks = request.context_chunks
    elif request.context:
        chunks = [
            ContextChunk(
                text=text,
                source_id=f"chunk_{i}",
                rank=i + 1,
                score=None,
                metadata={}
            )
            for i, text in enumerate(request.context)
        ]
    else:
        chunks = []

    return CanonicalEvaluation(
        query=request.query,
        response=request.response,
        context_chunks=chunks,
        ground_truth=request.ground_truth,
        metadata=request.metadata or {},
        framework=request.metadata.get("framework", "raw"),
        project_id=str(request.project_id),
        judge_model=request.metadata.get("judge_model", "gpt-4o-mini"),
        evaluator_version="3"
    )


def normalize_langchain_data(run_data: Dict) -> CanonicalEvaluation:
    """Convert LangChain callback data to canonical format"""
    return CanonicalEvaluation(
        query=run_data["query"],
        response=run_data["response"],
        context_chunks=[
            ContextChunk(**chunk) for chunk in run_data["context_chunks"]
        ],
        metadata=run_data.get("metadata", {}),
        framework="langchain",
        project_id=run_data["project_id"]
    )


def normalize_llamaindex_data(event_data: Dict) -> CanonicalEvaluation:
    """Convert LlamaIndex event data to canonical format"""
    return CanonicalEvaluation(
        query=event_data["query"],
        response=event_data["response"],
        context_chunks=[
            ContextChunk(**chunk) for chunk in event_data["context_chunks"]
        ],
        metadata=event_data.get("metadata", {}),
        framework="llama_index",
        project_id=event_data["project_id"]
    )
