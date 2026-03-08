"""
Layer D: Root Cause Engine — from EVALKIT_MASTER_SPEC_v2.md Section 6.
Hierarchical cascade: the FIRST matching condition wins as primary.
A secondary root cause captures the next match (if any).
Order matters — this is deterministic, not scored.
"""
import re
from typing import Optional
from evalkit.config import settings
from evalkit.models.enums import RootCauseCode, get_severity

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "of", "in", "to",
    "for", "with", "on", "at", "from", "by", "as", "into", "through",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "it", "its", "this", "that", "these", "those",
})


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r'\b\w+\b', text.lower()) if w not in _STOP_WORDS and len(w) > 1}


def _query_relevant_ctx_ids(query: str, contexts: list[dict], threshold: float = 0.15) -> set[str]:
    """Return context IDs that have meaningful token overlap with the query."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return {ctx.get("id", "") for ctx in contexts}
    relevant = set()
    for ctx in contexts:
        ctx_tokens = _tokenize(ctx.get("text", ""))
        overlap = len(query_tokens & ctx_tokens) / len(query_tokens) if query_tokens else 0
        if overlap >= threshold:
            relevant.add(ctx.get("id", ""))
    return relevant


def _find_novel_phrases(response_text: str, all_ctx_text: str) -> list[str]:
    """Find multi-word phrases in response absent from all context text.

    Splits response on commas/conjunctions, then checks each segment
    for presence in context. Returns segments with no overlap.
    """
    segments = re.split(r',\s*|\s+and\s+|\s+or\s+', response_text)
    ctx_tokens = _tokenize(all_ctx_text)
    novel = []
    for seg in segments:
        seg = seg.strip().rstrip(".")
        seg_tokens = _tokenize(seg)
        if len(seg_tokens) < 2:
            continue
        overlap = len(seg_tokens & ctx_tokens) / len(seg_tokens) if seg_tokens else 1
        if overlap < 0.25:
            novel.append(seg.strip())
    return novel


def determine_root_cause(
    query: str,
    response: str,
    contexts: list[dict],
    retrieval_metrics: dict,
    generation_metrics: dict | None = None,
    claim_results: dict | None = None,
    answerability: dict | None = None,
    hallucination_tier: dict | None = None,
    relevance_labels: dict[str, float] | None = None,
) -> dict:
    """Deterministic root cause analysis using hierarchical cascade.

    Returns dict with keys: code, message, severity, attribution, secondary.
    secondary is either None or a dict with code/message/severity/attribution.
    """
    checks = _build_checks(
        query, response, contexts, retrieval_metrics,
        generation_metrics, claim_results, answerability,
        hallucination_tier, relevance_labels,
    )

    hits: list[dict] = []
    for check_fn in checks:
        result = check_fn()
        if result is not None:
            hits.append(result)
            if len(hits) == 2:
                break

    if not hits:
        primary = _cause(RootCauseCode.PASS, "All evaluation checks passed", "cascade")
    else:
        primary = hits[0]

    primary["secondary"] = hits[1] if len(hits) >= 2 else None
    return primary


def _build_checks(
    query: str,
    response: str,
    contexts: list[dict],
    retrieval_metrics: dict,
    generation_metrics: dict | None,
    claim_results: dict | None,
    answerability: dict | None,
    hallucination_tier: dict | None,
    relevance_labels: dict[str, float] | None,
) -> list:
    """Build ordered list of check functions. Each returns a cause dict or None."""
    t = settings.thresholds
    checks = []

    # Step 1: Input Validation
    def check_empty_query():
        if not query or not query.strip():
            return _cause(RootCauseCode.INPUT_INVALID, "Query is empty", "input_validation")
    checks.append(check_empty_query)

    def check_no_contexts():
        if not contexts:
            return _cause(RootCauseCode.NO_CONTEXT_PROVIDED, "No contexts provided", "input_validation")
    checks.append(check_no_contexts)

    def check_empty_response():
        if not response or not response.strip():
            return _cause(RootCauseCode.NO_RESPONSE_GENERATED, "Response is empty", "input_validation")
    checks.append(check_empty_response)

    # Step 2: Answerability
    def check_should_have_refused():
        if answerability:
            classification = answerability.get("classification", "")
            if classification == "unanswerable" and response and response.strip():
                if not _looks_like_refusal(response):
                    return _cause(
                        RootCauseCode.SHOULD_HAVE_REFUSED,
                        "Query appears unanswerable from provided contexts, but RAG generated an answer instead of refusing",
                        "answerability",
                    )
    checks.append(check_should_have_refused)

    def check_false_refusal():
        if not response or not _looks_like_refusal(response):
            return None
        # Refusal-aware: use recall directly (claim support is always ~0 for refusal text)
        recall = retrieval_metrics.get("recall_at_k")
        if recall is not None and recall >= t.false_refusal_recall:
            return _cause(
                RootCauseCode.FALSE_REFUSAL,
                f"Response is a refusal but relevant contexts were retrieved (recall={recall:.2f}). Evidence is available to answer the query.",
                "answerability",
            )
        # Fallback: answerability-based check
        if answerability:
            classification = answerability.get("classification", "")
            if classification == "answerable":
                return _cause(
                    RootCauseCode.FALSE_REFUSAL,
                    "Evidence is available in contexts but RAG refused to answer",
                    "answerability",
                )
    checks.append(check_false_refusal)

    # Step 3: Retrieval Quality
    def check_no_relevant_docs():
        hit_rate = retrieval_metrics.get("hit_rate_at_k")
        if hit_rate is not None and hit_rate == 0:
            return _cause(
                RootCauseCode.NO_RELEVANT_DOCS_RETRIEVED,
                f"No relevant documents found in top-{retrieval_metrics.get('k', 'K')} results (hit_rate=0)",
                "layer_a",
            )
    checks.append(check_no_relevant_docs)

    def check_retrieval_miss():
        recall = retrieval_metrics.get("recall_at_k")
        if recall is not None and recall < t.recall_poor:
            return _cause(
                RootCauseCode.RETRIEVAL_MISS,
                f"Poor retrieval recall ({recall:.2f} < {t.recall_poor} threshold). Most relevant documents were not retrieved.",
                "layer_a",
            )
    checks.append(check_retrieval_miss)

    def check_excessive_noise():
        precision = retrieval_metrics.get("precision_at_k")
        if precision is not None and precision <= t.precision_poor and len(contexts) >= 5:
            return _cause(
                RootCauseCode.EXCESSIVE_NOISE,
                f"Very low retrieval precision ({precision:.2f} <= {t.precision_poor} threshold). Most retrieved documents are irrelevant.",
                "layer_a",
            )
    checks.append(check_excessive_noise)

    # Step 3b: Noise detection fallback
    def check_inferred_noise():
        precision = retrieval_metrics.get("precision_at_k")
        if precision is None and contexts and len(contexts) >= 3:
            query_relevant = _query_relevant_ctx_ids(query, contexts)
            if len(query_relevant) > 0:
                inferred_precision = len(query_relevant) / len(contexts)
                if inferred_precision < t.precision_poor:
                    return _cause(
                        RootCauseCode.EXCESSIVE_NOISE,
                        f"Inferred low retrieval precision ({inferred_precision:.2f}). Only {len(query_relevant)}/{len(contexts)} contexts appear relevant to the query.",
                        "layer_a",
                    )
    checks.append(check_inferred_noise)

    # Step 3.5: Hallucination Tier signal
    def check_hallucination_tier():
        if hallucination_tier is not None:
            ht_tier = hallucination_tier.get("tier_used", 1)
            ht_score = hallucination_tier.get("score", 0.0)
            ht_confidence = hallucination_tier.get("confidence", 0.0)
            if ht_tier >= 2 and ht_score > 0.7 and ht_confidence > 0.6:
                return _cause(
                    RootCauseCode.HALLUCINATION,
                    f"Hallucination detected by tier-{ht_tier} analysis (score={ht_score:.2f}, confidence={ht_confidence:.2f})",
                    f"hallucination_tier_{ht_tier}",
                )
    checks.append(check_hallucination_tier)

    # Step 4: Evidence Mapping (Layer C signals)
    def check_number_contradictions():
        if claim_results is not None:
            if claim_results.get("has_number_contradictions"):
                unsupported = claim_results.get("unsupported_claims", [])
                return _cause(
                    RootCauseCode.HALLUCINATION,
                    f"Response contains numbers that contradict the context. Unsupported claims: {unsupported[:3]}",
                    "layer_c",
                )
    checks.append(check_number_contradictions)

    def check_claim_support():
        if claim_results is not None:
            supported_pct = claim_results.get("supported_pct", 0)
            unsupported = claim_results.get("unsupported_claims", [])
            if supported_pct < t.claim_evidence_not_used and len(unsupported) > 0:
                if supported_pct < t.claim_hallucination:
                    return _cause(
                        RootCauseCode.HALLUCINATION,
                        f"Only {supported_pct:.0%} of claims are supported by context. Multiple unsupported claims detected: {unsupported[:3]}",
                        "layer_c",
                    )
                else:
                    return _cause(
                        RootCauseCode.EVIDENCE_NOT_USED,
                        f"Evidence exists in context but only {supported_pct:.0%} of claims use it. The model may be ignoring retrieved context.",
                        "layer_c",
                    )
    checks.append(check_claim_support)

    # Step 4b: Context Coverage
    def check_context_coverage():
        if claim_results is not None and contexts and len(contexts) > 1:
            used_ctx_ids = set()
            for claim in claim_results.get("claims", []):
                for evidence in claim.get("evidence", []):
                    used_ctx_ids.add(evidence["context_id"])
            if relevance_labels:
                relevant_ctx_ids = {cid for cid, score in relevance_labels.items() if score > 0}
            else:
                relevant_ctx_ids = _query_relevant_ctx_ids(query, contexts)
            coverage = len(used_ctx_ids & relevant_ctx_ids) / len(relevant_ctx_ids) if relevant_ctx_ids else 1.0
            if coverage < 0.5 and len(relevant_ctx_ids) >= 2:
                return _cause(
                    RootCauseCode.EVIDENCE_NOT_USED,
                    f"Response uses only {len(used_ctx_ids)}/{len(relevant_ctx_ids)} provided contexts ({coverage:.0%} coverage). Key evidence is being ignored.",
                    "layer_c",
                )
    checks.append(check_context_coverage)

    # Step 5: Generation Quality
    def check_low_faithfulness():
        if generation_metrics is not None:
            scores = generation_metrics if isinstance(generation_metrics, dict) else {}
            if "scores" in scores:
                scores = scores["scores"]
            faithfulness = scores.get("faithfulness")
            if faithfulness is not None and faithfulness < t.faithfulness_low:
                return _cause(
                    RootCauseCode.GENERATION_UNFAITHFUL,
                    f"Low faithfulness score ({faithfulness:.2f} < {t.faithfulness_low}). Response contains claims not grounded in context.",
                    "layer_b",
                )
    checks.append(check_low_faithfulness)

    def check_low_relevance():
        if generation_metrics is not None:
            scores = generation_metrics if isinstance(generation_metrics, dict) else {}
            if "scores" in scores:
                scores = scores["scores"]
            relevance = scores.get("answer_relevance")
            if relevance is not None and relevance < t.relevance_low:
                return _cause(
                    RootCauseCode.OFF_TOPIC_RESPONSE,
                    f"Low answer relevance ({relevance:.2f} < {t.relevance_low}). Response does not address the query.",
                    "layer_b",
                )
    checks.append(check_low_relevance)

    # Step 5b: Rule-based off-topic fallback
    def check_off_topic_fallback():
        relevance_score = None
        if generation_metrics is not None:
            gm_scores = generation_metrics.get("scores", generation_metrics)
            relevance_score = gm_scores.get("answer_relevance") if isinstance(gm_scores, dict) else None
        if relevance_score is None:
            query_tokens = _tokenize(query)
            response_tokens = _tokenize(response)
            if len(query_tokens) >= 2 and len(response_tokens) >= 3:
                qr_overlap = len(query_tokens & response_tokens) / len(query_tokens)
                if qr_overlap < 0.15 and claim_results is not None:
                    supported_pct = claim_results.get("supported_pct", 0)
                    if supported_pct >= 0.5:
                        return _cause(
                            RootCauseCode.OFF_TOPIC_RESPONSE,
                            f"Response is grounded in context but does not address the query (query-response overlap: {qr_overlap:.0%}). Likely answered wrong question.",
                            "layer_b",
                        )
    checks.append(check_off_topic_fallback)

    # Step 5c: Novel phrase detection
    def check_novel_phrases():
        faithfulness_score = None
        if generation_metrics is not None:
            gm_scores = generation_metrics.get("scores", generation_metrics)
            faithfulness_score = gm_scores.get("faithfulness") if isinstance(gm_scores, dict) else None
        if contexts and len(contexts) > 0:
            all_ctx_text = " ".join(ctx.get("text", "") for ctx in contexts).lower()
            novel_phrases = _find_novel_phrases(response.lower(), all_ctx_text)
            if len(novel_phrases) >= 1:
                if faithfulness_score is None or faithfulness_score < 0.8:
                    return _cause(
                        RootCauseCode.GENERATION_UNFAITHFUL,
                        f"Response introduces factual content not found in any context: {', '.join(novel_phrases[:3])}. Possible hallucination.",
                        "layer_b",
                    )
    checks.append(check_novel_phrases)

    return checks


def _cause(code: RootCauseCode, message: str, attribution: str) -> dict:
    return {
        "code": code.value,
        "message": message,
        "severity": get_severity(code.value),
        "attribution": attribution,
    }


def _looks_like_refusal(response: str) -> bool:
    """Simple heuristic to detect if a response is a refusal/IDK."""
    refusal_phrases = [
        "i don't know", "i do not know",
        "i cannot answer", "i can't answer",
        "i'm not sure", "i am not sure",
        "insufficient information", "not enough information",
        "no information available", "unable to answer",
        "cannot determine", "not able to determine",
        "i don't have enough", "i do not have enough",
        "i don't have access", "i do not have access",
        "i don't have information", "i do not have information",
        "i can't provide", "i cannot provide",
        "i'm unable to", "i am unable to",
        "based on the provided context, i cannot",
        "the context does not contain", "no relevant information",
        "please contact", "contact customer support",
    ]
    lower = response.lower().strip()
    return any(phrase in lower for phrase in refusal_phrases)
