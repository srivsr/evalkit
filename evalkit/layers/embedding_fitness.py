"""
Layer D.2: Embedding Domain Fitness — from EVALKIT_MASTER_SPEC_v2.md Section 6.

Tests whether an embedding model captures domain-specific semantics by computing
cosine similarity on user-provided term pairs.
"""
import logging
import math
from typing import Optional

from evalkit.config import settings

logger = logging.getLogger(__name__)

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = settings.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        try:
            from openai import AsyncOpenAI
            _openai_client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package required: pip install openai")
    return _openai_client


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def get_embeddings(texts: list[str], model: str) -> list[list[float]]:
    client = _get_openai_client()
    resp = await client.embeddings.create(input=texts, model=model)
    sorted_data = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in sorted_data]


async def evaluate_embedding_fitness(
    project_id: str,
    embedding_model: str,
    domain: Optional[str],
    term_pairs: list[dict],
    similarity_threshold: float,
) -> dict:
    unique_terms = list({t for p in term_pairs for t in (p["term_a"], p["term_b"])})
    term_to_idx = {t: i for i, t in enumerate(unique_terms)}

    vectors = await get_embeddings(unique_terms, embedding_model)

    results = []
    passed_count = 0
    for pair in term_pairs:
        vec_a = vectors[term_to_idx[pair["term_a"]]]
        vec_b = vectors[term_to_idx[pair["term_b"]]]
        sim = round(_cosine_similarity(vec_a, vec_b), 4)

        if pair["expected"] == "similar":
            passed = sim >= similarity_threshold
        else:
            passed = sim < similarity_threshold

        if passed:
            passed_count += 1

        results.append({
            "term_a": pair["term_a"],
            "term_b": pair["term_b"],
            "expected": pair["expected"],
            "similarity": sim,
            "passed": passed,
        })

    total = len(term_pairs)
    fitness_score = round(passed_count / total, 4) if total > 0 else 0.0

    recommendations = _generate_recommendations(results, similarity_threshold, domain)
    root_cause = "EMBEDDING_DOMAIN_MISMATCH" if fitness_score < 0.5 else None

    return {
        "project_id": project_id,
        "embedding_model": embedding_model,
        "domain": domain,
        "fitness_score": fitness_score,
        "total_pairs": total,
        "passed_pairs": passed_count,
        "failed_pairs": total - passed_count,
        "results": results,
        "recommendations": recommendations,
        "root_cause": root_cause,
    }


def _generate_recommendations(
    results: list[dict], threshold: float, domain: Optional[str]
) -> list[str]:
    recs = []
    failed_similar = [r for r in results if r["expected"] == "similar" and not r["passed"]]
    failed_dissimilar = [r for r in results if r["expected"] == "dissimilar" and not r["passed"]]

    if failed_similar:
        pairs_str = ", ".join(
            f'"{r["term_a"]}" / "{r["term_b"]}" ({r["similarity"]:.2f})'
            for r in failed_similar[:3]
        )
        recs.append(
            f"Similar terms scored below threshold ({threshold}): {pairs_str}. "
            f"Consider fine-tuning or using a domain-specific model."
        )

    if failed_dissimilar:
        pairs_str = ", ".join(
            f'"{r["term_a"]}" / "{r["term_b"]}" ({r["similarity"]:.2f})'
            for r in failed_dissimilar[:3]
        )
        recs.append(
            f"Dissimilar terms scored above threshold ({threshold}): {pairs_str}. "
            f"The model may lack domain discrimination."
        )

    if domain and (failed_similar or failed_dissimilar):
        recs.append(
            f"Domain '{domain}': evaluate a model fine-tuned on {domain} corpora."
        )

    return recs
