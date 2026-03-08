"""Layer D.0: Answerability Detection — from EVALKIT_MASTER_SPEC_v2.md Section 6."""
from evalkit.config import settings
from evalkit.models.enums import AnswerabilityClass


def classify_answerability(
    retrieval_metrics: dict,
    claim_results: dict | None = None,
) -> dict:
    """
    Classify whether the query is answerable given the retrieved contexts.
    Phase 1: Rule-based, derived from retrieval metrics + claim support.
    """
    supported_pct = 0.0
    if claim_results and "supported_pct" in claim_results:
        supported_pct = claim_results["supported_pct"]

    recall = retrieval_metrics.get("recall_at_k")
    hit_rate = retrieval_metrics.get("hit_rate_at_k")

    t = settings.thresholds
    # When claim results available (Week 3+), use spec algorithm
    if claim_results and "supported_pct" in claim_results:
        if supported_pct >= t.answerability_strong:
            return _result(
                AnswerabilityClass.ANSWERABLE,
                f"Strong evidence support ({supported_pct:.0%} of claims supported)",
                "Should answer confidently",
            )
        elif supported_pct >= t.answerability_partial:
            return _result(
                AnswerabilityClass.PARTIALLY_ANSWERABLE,
                f"Partial evidence support ({supported_pct:.0%} of claims supported)",
                "Should answer with caveats",
            )
        else:
            if recall is not None and recall < t.answerability_recall_unanswerable:
                return _result(
                    AnswerabilityClass.UNANSWERABLE,
                    f"Very low claim support ({supported_pct:.0%}) and poor recall ({recall:.2f}). Evidence likely doesn't exist in knowledge base.",
                    "Should refuse or say 'I don't know'",
                )
            elif recall is None and supported_pct < t.claim_hallucination and not _any_claim_has_evidence(claim_results):
                return _result(
                    AnswerabilityClass.UNANSWERABLE,
                    f"Very low claim support ({supported_pct:.0%}) with no retrieval ground truth and no evidence spans found. Contexts appear irrelevant to the response.",
                    "Should refuse or say 'I don't know'",
                )
            else:
                return _result(
                    AnswerabilityClass.PARTIALLY_ANSWERABLE,
                    f"Low claim support ({supported_pct:.0%}) but recall suggests evidence may exist. Possible retrieval or generation issue.",
                    "Should answer with caveats",
                )

    # Week 2 fallback: retrieval signals only
    if recall is not None and hit_rate is not None:
        if hit_rate == 0:
            return _result(
                AnswerabilityClass.UNANSWERABLE,
                "No relevant documents found in top-K results (hit_rate=0)",
                "Should refuse or say 'I don't know'",
            )
        elif recall >= t.answerability_recall_high:
            return _result(
                AnswerabilityClass.ANSWERABLE,
                f"Good retrieval recall ({recall:.2f}), evidence likely present",
                "Should answer confidently",
            )
        elif recall >= t.answerability_recall_mid:
            return _result(
                AnswerabilityClass.PARTIALLY_ANSWERABLE,
                f"Moderate retrieval recall ({recall:.2f}), some evidence present",
                "Should answer with caveats",
            )
        else:
            return _result(
                AnswerabilityClass.UNANSWERABLE,
                f"Poor retrieval recall ({recall:.2f}), evidence likely missing",
                "Should refuse or say 'I don't know'",
            )

    return _result(
        AnswerabilityClass.PARTIALLY_ANSWERABLE,
        "Insufficient signals to determine answerability (no ground truth or claim data)",
        "Should answer with caveats",
    )


def _any_claim_has_evidence(claim_results: dict | None) -> bool:
    """Check if any claim has evidence spans, indicating contexts are topically relevant."""
    if not claim_results:
        return False
    for claim in claim_results.get("claims", []):
        if claim.get("evidence"):
            return True
    return False


def _result(classification: AnswerabilityClass, rationale: str, expected_behavior: str) -> dict:
    return {
        "classification": classification.value,
        "rationale": rationale,
        "expected_behavior": expected_behavior,
    }
