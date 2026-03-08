"""
Auto-escalation logic for multi-judge consensus — Week 5.

Starts with the cheapest judge, measures confidence from structural signals,
and escalates to multi-judge only when confidence is below threshold.
"""
import logging

from evalkit.judges.base import BaseJudge
from evalkit.judges.consensus import run_consensus
from evalkit.layers.cost_tracker import MODEL_PRICING, DEFAULT_PRICING

logger = logging.getLogger(__name__)


def get_models_by_cost(models: list[str], ascending: bool = True) -> list[str]:
    def _total_cost(model: str) -> float:
        p = MODEL_PRICING.get(model, DEFAULT_PRICING)
        return p["input"] + p["output"]
    return sorted(models, key=_total_cost, reverse=not ascending)


def compute_single_judge_confidence(result: dict) -> float:
    signals = []
    faith = result.get("faithfulness", 0.0)
    signals.append(1.0 if faith > 0.0 else 0.0)
    rel = result.get("answer_relevance", 0.0)
    signals.append(1.0 if rel > 0.0 else 0.0)
    per_judge = result.get("per_judge", [])
    claims = per_judge[0].get("faithfulness_claims", []) if per_judge else []
    if len(claims) >= 3:
        signals.append(1.0)
    elif len(claims) >= 1:
        signals.append(0.5)
    else:
        signals.append(0.0)
    return sum(signals) / len(signals) if signals else 0.5


async def run_escalation(
    judges: list[BaseJudge],
    query: str,
    response: str,
    contexts: list[str],
    confidence_threshold: float = 0.75,
    timeout_ms: int = 30000,
    cost_cap_usd: float | None = None,
) -> dict:
    if not judges:
        return {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "confidence": {
                "mode": "auto_no_judges",
                "judge_count": 0,
                "agreement_pct": None,
                "escalated": False,
                "escalation_reason": None,
            },
            "per_judge": [],
            "disagreement_notes": [],
            "prompt_version": None,
        }

    sorted_models = get_models_by_cost([j.model_name for j in judges])
    sorted_judges = sorted(judges, key=lambda j: sorted_models.index(j.model_name))

    cheap_result = await run_consensus(
        judges=[sorted_judges[0]],
        query=query,
        response=response,
        contexts=contexts,
        timeout_ms=timeout_ms,
        cost_cap_usd=cost_cap_usd,
    )

    confidence = compute_single_judge_confidence(cheap_result)

    if confidence >= confidence_threshold:
        cheap_result["confidence"]["mode"] = "auto_single"
        cheap_result["confidence"]["escalated"] = False
        cheap_result["confidence"]["escalation_reason"] = None
        return cheap_result

    if len(sorted_judges) < 2:
        cheap_result["confidence"]["mode"] = "auto_single"
        cheap_result["confidence"]["escalated"] = False
        cheap_result["confidence"]["escalation_reason"] = "insufficient_judges_for_escalation"
        return cheap_result

    if cost_cap_usd is not None and cost_cap_usd <= 0:
        cheap_result["confidence"]["mode"] = "auto_single"
        cheap_result["confidence"]["escalated"] = False
        cheap_result["confidence"]["escalation_reason"] = "cost_cap_prevented_escalation"
        return cheap_result

    logger.info(
        f"Auto-escalation triggered: confidence={confidence:.2f} < threshold={confidence_threshold}"
    )

    multi_result = await run_consensus(
        judges=sorted_judges,
        query=query,
        response=response,
        contexts=contexts,
        timeout_ms=timeout_ms,
        cost_cap_usd=cost_cap_usd,
    )

    multi_result["confidence"]["mode"] = "auto_multi"
    multi_result["confidence"]["escalated"] = True
    multi_result["confidence"]["escalation_reason"] = (
        f"confidence_{confidence:.2f}_below_threshold_{confidence_threshold}"
    )
    return multi_result
