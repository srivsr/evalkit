"""
Fix Suggestions Engine — template-based recommendations from root cause.

Each root cause code maps to actionable fix suggestions.
Priority: high = must fix, medium = should fix, low = nice to fix.
"""
from evalkit.models.enums import SEVERITY_MAP


FIX_TEMPLATES: dict[str, list[dict]] = {
    "INPUT_INVALID": [
        {"target": "pipeline", "action": "Validate inputs before sending to RAG pipeline", "priority": "high", "detail": "Ensure query is non-empty and well-formed before evaluation."},
    ],
    "NO_CONTEXT_PROVIDED": [
        {"target": "retrieval", "action": "Check retrieval pipeline — no contexts were returned", "priority": "high", "detail": "Verify vector store connection, embedding model, and retrieval configuration."},
    ],
    "NO_RESPONSE_GENERATED": [
        {"target": "generation", "action": "Check LLM generation — no response was produced", "priority": "high", "detail": "Verify LLM API connection, prompt template, and error handling."},
    ],
    "SHOULD_HAVE_REFUSED": [
        {"target": "generation", "action": "Add refusal guardrails for unanswerable queries", "priority": "high", "detail": "Configure the LLM to say 'I don't know' when context doesn't contain answer evidence."},
        {"target": "retrieval", "action": "Consider adding an answerability check before generation", "priority": "medium"},
    ],
    "FALSE_REFUSAL": [
        {"target": "generation", "action": "Tune refusal threshold — model is refusing valid queries", "priority": "high", "detail": "The LLM is being too conservative. Adjust system prompt or confidence thresholds."},
    ],
    "RETRIEVAL_MISS": [
        {"target": "retrieval", "action": "Improve retrieval recall — most relevant documents not retrieved", "priority": "high", "detail": "Consider: increasing top-K, trying different embedding models, adding query expansion."},
        {"target": "indexing", "action": "Verify indexing completeness", "priority": "medium", "detail": "Ensure all relevant documents are indexed and embeddings are up to date."},
    ],
    "NO_RELEVANT_DOCS_RETRIEVED": [
        {"target": "retrieval", "action": "No relevant documents in top-K — retrieval pipeline failing", "priority": "high", "detail": "Check: embedding model domain fitness, chunk quality, similarity threshold."},
        {"target": "indexing", "action": "Re-index with domain-appropriate embedding model", "priority": "high"},
    ],
    "EXCESSIVE_NOISE": [
        {"target": "retrieval", "action": "Reduce retrieval noise — too many irrelevant documents", "priority": "medium", "detail": "Consider: reducing top-K, adding a reranker, increasing similarity threshold."},
    ],
    "EVIDENCE_NOT_USED": [
        {"target": "generation", "action": "Model ignoring context — strengthen grounding instructions", "priority": "high", "detail": "Update system prompt to emphasize answering ONLY from provided context."},
    ],
    "HALLUCINATION": [
        {"target": "generation", "action": "Critical: model generating unsupported claims", "priority": "high", "detail": "Add strict grounding instructions. Consider switching to a more faithful model."},
        {"target": "generation", "action": "Enable citation requirements in the prompt template", "priority": "medium"},
    ],
    "GENERATION_UNFAITHFUL": [
        {"target": "generation", "action": "Improve faithfulness — response not grounded in context", "priority": "high", "detail": "Strengthen system prompt grounding. Consider temperature=0 for deterministic output."},
    ],
    "OFF_TOPIC_RESPONSE": [
        {"target": "generation", "action": "Response doesn't address the query — check query understanding", "priority": "high", "detail": "Ensure the query is clearly included in the prompt. Consider query reformulation."},
    ],
    "CHUNK_BOUNDARY_BROKEN": [
        {"target": "chunking", "action": "Fix chunk boundaries — sentences split mid-text", "priority": "medium", "detail": "Use sentence-aware chunking. Ensure chunks end at natural sentence boundaries."},
    ],
    "CHUNK_INCOHERENT": [
        {"target": "chunking", "action": "Improve chunk coherence — chunks lack standalone meaning", "priority": "low", "detail": "Add overlap between chunks or include context headers."},
    ],
    "CHUNK_TOO_SPARSE": [
        {"target": "chunking", "action": "Increase chunk size — current chunks too small for effective retrieval", "priority": "low"},
    ],
    "CHUNK_TOO_DENSE": [
        {"target": "chunking", "action": "Decrease chunk size — current chunks too large for precise retrieval", "priority": "low"},
    ],
    "EMBEDDING_DOMAIN_MISMATCH": [
        {"target": "indexing", "action": "Embedding model lacks domain semantics — consider fine-tuning or switching models", "priority": "high", "detail": "Run /v1/evaluate/embeddings with domain term pairs to identify gaps."},
    ],
    "EMBEDDING_DRIFT": [
        {"target": "indexing", "action": "Embedding model performance has drifted — re-evaluate with current term pairs", "priority": "medium", "detail": "Compare current fitness score with baseline. Re-index if model was updated."},
    ],
    "PASS": [],
}


def generate_fix_suggestions(root_cause_code: str, context: dict | None = None) -> list[dict]:
    suggestions = FIX_TEMPLATES.get(root_cause_code, [])

    if context and context.get("k", 0) > 5:
        k = context["k"]
        ndcg = context.get("ndcg_at_k")
        if ndcg is not None and ndcg > 0.8:
            suggestions = suggestions + [{
                "target": "retrieval",
                "action": f"Consider reducing K from {k} to 5",
                "priority": "low",
                "detail": f"NDCG is high ({ndcg:.2f}), suggesting good results are in top positions. Reducing K saves evaluation cost with minimal quality impact.",
            }]

    return suggestions
