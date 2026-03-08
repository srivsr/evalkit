"""Layer A: Retrieval Quality — from EVALKIT_MASTER_SPEC_v2.md Section 6."""
import math
from evalkit.config import settings


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    return len(set(top_k) & relevant) / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    top_k = retrieved[:k]
    return len(set(top_k) & relevant) / len(relevant) if relevant else 0.0


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    for i, doc in enumerate(retrieved):
        if doc in relevant:
            return 1.0 / (i + 1)
    return 0.0


def hit_rate_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if set(retrieved[:k]) & relevant else 0.0


def ndcg_at_k(retrieved: list[str], relevance_scores: dict[str, float], k: int) -> float:
    dcg = sum(
        relevance_scores.get(doc, 0) / math.log2(i + 2)
        for i, doc in enumerate(retrieved[:k])
    )
    ideal = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = sum(score / math.log2(i + 2) for i, score in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def compute_retrieval_metrics(
    context_ids: list[str],
    relevance_labels: dict[str, float] | None,
    k: int,
) -> dict:
    """Compute all Layer A classical retrieval metrics."""
    result = {
        "precision_at_k": None,
        "recall_at_k": None,
        "mrr": None,
        "ndcg_at_k": None,
        "hit_rate_at_k": None,
        "context_coverage": None,
        "k": k,
    }

    if relevance_labels is None:
        return result

    t = settings.thresholds.relevance_label_threshold
    relevant = {ctx_id for ctx_id, score in relevance_labels.items() if score >= t}

    result["precision_at_k"] = precision_at_k(context_ids, relevant, k)
    result["recall_at_k"] = recall_at_k(context_ids, relevant, k)
    result["mrr"] = mrr(context_ids, relevant)
    result["hit_rate_at_k"] = hit_rate_at_k(context_ids, relevant, k)
    result["ndcg_at_k"] = ndcg_at_k(context_ids, relevance_labels, k)

    return result
