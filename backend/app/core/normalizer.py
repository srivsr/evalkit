from typing import List
from ..schemas import EvaluateRequest, CanonicalEvaluation, ContextChunk


def normalize_request(request: EvaluateRequest) -> CanonicalEvaluation:
    if request.context_chunks:
        context_chunks = request.context_chunks
    elif request.context:
        context_chunks = [
            ContextChunk(text=text, rank=i + 1)
            for i, text in enumerate(request.context)
        ]
    else:
        context_chunks = []

    return CanonicalEvaluation(
        query=request.query,
        response=request.response,
        context_chunks=context_chunks,
        ground_truth=request.ground_truth,
        metadata=request.metadata,
        evaluator_version="3"
    )
