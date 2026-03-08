"""Tiered Hallucination Detection — Week 7.

Tier 1: Deterministic (claims.py supported_pct) — free, fast
Tier 2: LLM judge faithfulness (generation.py) — already computed
Tier 3: Specialized detection prompt via BaseJudge._call_llm()
"""
import json
import logging
from typing import Optional

from evalkit.judges.base import BaseJudge, parse_json_response

logger = logging.getLogger(__name__)

TIER3_PROMPT = """You are a hallucination detector. Analyze the response for factual errors against the provided context.

CONTEXT:
{contexts_joined}

QUERY:
{query}

RESPONSE:
{response}

Check these 4 dimensions:
1. ENTITY ACCURACY: Are all named entities (people, places, orgs, products) correct per context?
2. NUMBER VERIFICATION: Are all numbers, dates, percentages, amounts accurate per context?
3. LOGICAL CONSISTENCY: Does the response contain internal contradictions or invalid inferences?
4. TEMPORAL FACTS: Are time references, event ordering, and temporal claims correct?

OUTPUT FORMAT (strict JSON, no other text):
{{
  "hallucination_score": 0.0,
  "entity_errors": ["error description"],
  "number_errors": ["error description"],
  "logic_errors": ["error description"],
  "temporal_errors": ["error description"]
}}

Score 0.0 = no hallucination, 1.0 = fully hallucinated. List only actual errors found."""


def tier1_score(claim_results: dict) -> dict:
    supported_pct = claim_results.get("supported_pct", 0.0)
    score = round(1.0 - supported_pct, 4)
    confidence = _compute_tier1_confidence(claim_results)
    half_width = 0.3 * (1.0 - confidence)
    ci_lower = max(0.0, round(score - half_width, 4))
    ci_upper = min(1.0, round(score + half_width, 4))
    return {
        "score": score,
        "confidence": round(confidence, 4),
        "confidence_interval": [ci_lower, ci_upper],
        "method": "deterministic",
    }


def _compute_tier1_confidence(claim_results: dict) -> float:
    claims = claim_results.get("claims", [])
    count = len(claims)
    if count == 0:
        return 0.3
    base = min(0.5 + count * 0.05, 0.85)
    if claim_results.get("has_number_contradictions"):
        base = min(base + 0.1, 0.95)
    partial = sum(1 for c in claims if c.get("support") == "partially_supported")
    if partial > count * 0.5:
        base *= 0.8
    return round(min(base, 1.0), 4)


def select_tier(
    requested_tier: str,
    tier1_result: dict,
    cost_cap_usd: Optional[float],
    has_judges: bool,
) -> int:
    if requested_tier in ("1", "2", "3"):
        return int(requested_tier)
    if cost_cap_usd is not None and cost_cap_usd == 0:
        return 1
    if not has_judges:
        return 1
    if tier1_result["confidence"] >= 0.8:
        return 1
    if tier1_result["score"] > 0.5:
        return 3
    return 2


async def tier3_evaluate(
    judge: BaseJudge,
    query: str,
    response: str,
    contexts: list[str],
) -> dict:
    contexts_joined = "\n\n---\n\n".join(contexts)
    prompt = TIER3_PROMPT.format(
        contexts_joined=contexts_joined, query=query, response=response,
    )
    raw = await judge._call_llm(prompt)
    parsed = parse_json_response(raw)
    return {
        "score": float(parsed.get("hallucination_score", 0.0)),
        "entity_errors": parsed.get("entity_errors", []),
        "number_errors": parsed.get("number_errors", []),
        "logic_errors": parsed.get("logic_errors", []),
        "temporal_errors": parsed.get("temporal_errors", []),
    }


def _aggregate_scores(
    tier1: dict,
    tier2_faithfulness: Optional[float],
    tier3: Optional[dict],
    tier_used: int,
) -> dict:
    if tier_used == 1:
        return {
            "score": tier1["score"],
            "confidence": tier1["confidence"],
            "confidence_interval": tier1["confidence_interval"],
        }

    t1_score = tier1["score"]
    if tier_used == 2 and tier2_faithfulness is not None:
        t2_score = round(1.0 - tier2_faithfulness, 4)
        score = round(0.4 * t1_score + 0.6 * t2_score, 4)
        confidence = min(round(tier1["confidence"] + 0.15, 4), 0.95)
        half_width = 0.2 * (1.0 - confidence)
    elif tier_used == 3 and tier3 is not None:
        t2_score = round(1.0 - tier2_faithfulness, 4) if tier2_faithfulness is not None else t1_score
        t3_score = tier3["score"]
        score = round(0.2 * t1_score + 0.3 * t2_score + 0.5 * t3_score, 4)
        confidence = min(round(tier1["confidence"] + 0.25, 4), 0.98)
        half_width = 0.1 * (1.0 - confidence)
    else:
        return {
            "score": tier1["score"],
            "confidence": tier1["confidence"],
            "confidence_interval": tier1["confidence_interval"],
        }

    ci_lower = max(0.0, round(score - half_width, 4))
    ci_upper = min(1.0, round(score + half_width, 4))
    return {"score": score, "confidence": confidence, "confidence_interval": [ci_lower, ci_upper]}


async def run_hallucination_tiering(
    query: str,
    response: str,
    contexts: list[str],
    claim_results: dict,
    generation_result: dict,
    judges: list[BaseJudge],
    requested_tier: str = "auto",
    cost_cap_usd: Optional[float] = None,
) -> dict:
    t1 = tier1_score(claim_results)
    tier = select_tier(requested_tier, t1, cost_cap_usd, bool(judges))

    tier2_faithfulness = None
    tier3_result = None
    fallback_used = False
    fallback_reason = None
    method = "deterministic"

    if tier >= 2:
        scores = generation_result.get("scores", {})
        tier2_faithfulness = scores.get("faithfulness")
        method = "judge_faithfulness"

    if tier == 3:
        method = "specialized_detection"
        try:
            tier3_result = await tier3_evaluate(judges[0], query, response, contexts)
        except Exception as e:
            logger.warning(f"Tier 3 hallucination detection failed: {e}")
            fallback_used = True
            fallback_reason = f"tier3_error: {e}"
            if tier2_faithfulness is not None:
                tier = 2
                method = "judge_faithfulness"
            else:
                tier = 1
                method = "deterministic"

    agg = _aggregate_scores(t1, tier2_faithfulness, tier3_result, tier)

    detail = None
    if tier3_result:
        detail = {
            "entity_errors": tier3_result.get("entity_errors", []),
            "number_errors": tier3_result.get("number_errors", []),
            "logic_errors": tier3_result.get("logic_errors", []),
            "temporal_errors": tier3_result.get("temporal_errors", []),
        }

    return {
        "tier_used": tier,
        "score": agg["score"],
        "confidence": agg["confidence"],
        "confidence_interval": agg["confidence_interval"],
        "method": method,
        "detail": detail,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
    }
