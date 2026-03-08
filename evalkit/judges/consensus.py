"""
Multi-judge consensus — from EVALKIT_MASTER_SPEC_v2.md Section 6 (Layer B).

Rules:
- Minimum 1 judge (single mode)
- 2+ judges for consensus
- Agreement = % of judges within 0.15 of each other
- Timeout -> fallback to first successful judge
- Cost cap -> stop and report partial consensus
"""
import asyncio
import logging

from evalkit.judges.base import BaseJudge

logger = logging.getLogger(__name__)


async def run_consensus(
    judges: list[BaseJudge],
    query: str,
    response: str,
    contexts: list[str],
    timeout_ms: int = 30000,
    cost_cap_usd: float | None = None,
) -> dict:
    if not judges:
        return _empty_result("no_judges")

    if len(judges) == 1:
        return await _single_judge(judges[0], query, response, contexts)

    timeout_s = timeout_ms / 1000
    results = []
    running_cost = 0.0

    tasks = [
        asyncio.create_task(_run_judge_safe(judge, query, response, contexts))
        for judge in judges
    ]

    try:
        completed = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        logger.warning("Multi-judge timeout — using partial results")
        completed = []
        for task in tasks:
            if task.done() and not task.cancelled():
                try:
                    completed.append(task.result())
                except Exception:
                    pass
            else:
                task.cancel()

    for r in completed:
        if isinstance(r, dict) and "faithfulness" in r:
            results.append(r)
            cost = r.get("cost_usd", 0.0)
            running_cost += cost
            if cost_cap_usd is not None and running_cost >= cost_cap_usd:
                logger.warning(f"Cost cap reached ({running_cost:.4f} >= {cost_cap_usd}), stopping early")
                break

    if not results:
        return _empty_result("all_judges_failed")

    if len(results) == 1:
        return _format_single(results[0], mode="multi_judge_fallback")

    faithfulness_scores = [r["faithfulness"] for r in results]
    relevance_scores = [r["answer_relevance"] for r in results]

    consensus_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
    consensus_relevance = sum(relevance_scores) / len(relevance_scores)

    faith_agreement = _compute_agreement(faithfulness_scores, threshold=0.15)
    rel_agreement = _compute_agreement(relevance_scores, threshold=0.15)
    overall_agreement = (faith_agreement + rel_agreement) / 2

    disagreements = []
    if faith_agreement < 1.0:
        disagreements.append(
            f"Faithfulness disagreement: scores={[round(s, 2) for s in faithfulness_scores]}"
        )
    if rel_agreement < 1.0:
        disagreements.append(
            f"Relevance disagreement: scores={[round(s, 2) for s in relevance_scores]}"
        )

    return {
        "faithfulness": round(consensus_faithfulness, 4),
        "answer_relevance": round(consensus_relevance, 4),
        "confidence": {
            "mode": "multi_judge",
            "judge_count": len(results),
            "agreement_pct": round(overall_agreement * 100, 1),
            "escalated": False,
            "escalation_reason": None,
        },
        "per_judge": [
            {"model": r.get("model", "unknown"), "faithfulness": r["faithfulness"], "answer_relevance": r["answer_relevance"]}
            for r in results
        ],
        "disagreement_notes": disagreements,
        "prompt_version": results[0].get("prompt_version") if results else None,
    }


async def _single_judge(judge: BaseJudge, query: str, response: str, contexts: list[str]) -> dict:
    result = await _run_judge_safe(judge, query, response, contexts)
    if isinstance(result, dict) and "faithfulness" in result:
        return _format_single(result, mode="single_judge")
    return _empty_result("judge_failed")


async def _run_judge_safe(judge: BaseJudge, query: str, response: str, contexts: list[str]) -> dict:
    try:
        faith_result = await judge.evaluate_faithfulness(query, response, contexts)
        rel_result = await judge.evaluate_relevance(query, response)
        return {
            "model": judge.model_name,
            "faithfulness": faith_result.get("faithfulness", 0.0),
            "answer_relevance": rel_result.get("answer_relevance", 0.0),
            "faithfulness_claims": faith_result.get("claims", []),
            "prompt_version": faith_result.get("prompt_version"),
        }
    except Exception as e:
        logger.error(f"Judge {judge.model_name} failed: {e}")
        return {"error": str(e)}


def _compute_agreement(scores: list[float], threshold: float = 0.15) -> float:
    if len(scores) < 2:
        return 1.0

    pairs = 0
    agreed = 0
    for i in range(len(scores)):
        for j in range(i + 1, len(scores)):
            pairs += 1
            if abs(scores[i] - scores[j]) <= threshold:
                agreed += 1

    return agreed / pairs if pairs > 0 else 1.0


def _format_single(result: dict, mode: str) -> dict:
    return {
        "faithfulness": result.get("faithfulness", 0.0),
        "answer_relevance": result.get("answer_relevance", 0.0),
        "confidence": {
            "mode": mode,
            "judge_count": 1,
            "agreement_pct": None,
            "escalated": False,
            "escalation_reason": None,
        },
        "per_judge": [
            {"model": result.get("model", "unknown"), "faithfulness": result.get("faithfulness", 0.0), "answer_relevance": result.get("answer_relevance", 0.0)}
        ],
        "disagreement_notes": [],
        "prompt_version": result.get("prompt_version"),
    }


def _empty_result(mode: str) -> dict:
    return {
        "faithfulness": 0.0,
        "answer_relevance": 0.0,
        "confidence": {"mode": mode, "judge_count": 0, "agreement_pct": None, "escalated": False, "escalation_reason": None},
        "per_judge": [],
        "disagreement_notes": [],
        "prompt_version": None,
    }
