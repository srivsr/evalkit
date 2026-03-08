"""
Layer B: Generation Quality — from EVALKIT_MASTER_SPEC_v2.md Section 6.

Orchestrates judge creation and evaluation.
Single-judge is default. Multi-judge behind config flag.
"""
import logging

from evalkit.judges.base import BaseJudge
from evalkit.judges.openai_judge import OpenAIJudge
from evalkit.judges.anthropic_judge import AnthropicJudge
from evalkit.judges.consensus import run_consensus
from evalkit.judges.escalation import run_escalation
from evalkit.config import settings

logger = logging.getLogger(__name__)


def create_judges(judge_models: list[str]) -> list[BaseJudge]:
    judges = []
    for model in judge_models:
        try:
            if "gpt" in model.lower() or "o1" in model.lower() or "o3" in model.lower():
                if settings.openai_api_key:
                    judges.append(OpenAIJudge(model=model))
                else:
                    logger.warning(f"Skipping {model}: no OPENAI_API_KEY configured")
            elif "claude" in model.lower() or "anthropic" in model.lower():
                if settings.anthropic_api_key:
                    judges.append(AnthropicJudge(model=model))
                else:
                    logger.warning(f"Skipping {model}: no ANTHROPIC_API_KEY configured")
            else:
                if settings.openai_api_key:
                    judges.append(OpenAIJudge(model=model))
        except Exception as e:
            logger.error(f"Failed to create judge for {model}: {e}")

    return judges


async def evaluate_generation(
    query: str,
    response: str,
    contexts: list[str],
    judge_mode: str = "auto",
    judge_models: list[str] | None = None,
    timeout_ms: int = 30000,
    cost_cap_usd: float | None = None,
    confidence_threshold: float = 0.75,
    escalation_models: list[str] | None = None,
) -> dict:
    if judge_models is None:
        judge_models = [settings.default_judge]

    all_model_names = list(dict.fromkeys(judge_models + (escalation_models or [])))
    judges = create_judges(all_model_names)

    if not judges:
        logger.warning("No judges available — returning zero scores")
        return {
            "scores": {"faithfulness": None, "answer_relevance": None},
            "judge_model": None,
            "confidence": {"mode": "no_judges", "judge_count": 0, "agreement_pct": None, "escalated": False, "escalation_reason": None},
            "claims": [],
            "prompt_version": None,
        }

    if judge_mode == "single":
        judges = judges[:1]
        result = await run_consensus(
            judges=judges, query=query, response=response,
            contexts=contexts, timeout_ms=timeout_ms, cost_cap_usd=cost_cap_usd,
        )
    elif judge_mode == "multi":
        result = await run_consensus(
            judges=judges, query=query, response=response,
            contexts=contexts, timeout_ms=timeout_ms, cost_cap_usd=cost_cap_usd,
        )
    else:
        result = await run_escalation(
            judges=judges, query=query, response=response,
            contexts=contexts, confidence_threshold=confidence_threshold,
            timeout_ms=timeout_ms, cost_cap_usd=cost_cap_usd,
        )

    return {
        "scores": {
            "faithfulness": result.get("faithfulness"),
            "answer_relevance": result.get("answer_relevance"),
        },
        "judge_model": result.get("per_judge", [{}])[0].get("model") if result.get("per_judge") else None,
        "confidence": result.get("confidence", {}),
        "claims": result.get("per_judge", [{}])[0].get("faithfulness_claims", []) if result.get("per_judge") else [],
        "prompt_version": result.get("prompt_version"),
    }
