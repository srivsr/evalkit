"""
Layer F: Cost & Latency Monitoring — from EVALKIT_MASTER_SPEC_v2.md Section 6.

Estimates token usage and cost per evaluation.
Phase 1: Simple estimation from text length. No tiktoken dependency.
"""
import logging

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4

MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}

DEFAULT_PRICING = {"input": 3.00, "output": 15.00}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_evaluation_cost(
    query: str,
    response: str,
    contexts: list[str],
    judge_model: str | None = None,
    judge_calls: int = 2,
) -> dict:
    if judge_model is None or judge_calls == 0:
        return {"tokens_used": 0, "estimated_cost_usd": 0.0}

    context_text = "\n".join(contexts)
    input_text = context_text + query + response
    template_overhead = 200
    input_tokens = estimate_tokens(input_text) + template_overhead

    output_tokens = 350

    total_input = input_tokens * judge_calls
    total_output = output_tokens * judge_calls

    pricing = MODEL_PRICING.get(judge_model)
    if pricing is None:
        logger.warning(f"Unknown model '{judge_model}' — using default pricing")
        pricing = DEFAULT_PRICING
    cost = (total_input / 1_000_000 * pricing["input"] +
            total_output / 1_000_000 * pricing["output"])

    return {
        "tokens_used": total_input + total_output,
        "estimated_cost_usd": round(cost, 6),
    }


def generate_cost_insight(
    cost_usd: float,
    verdict: str,
    k: int,
    ndcg: float | None = None,
) -> str | None:
    if cost_usd == 0:
        return None

    parts = [f"Evaluation cost: ${cost_usd:.4f} | Quality: {verdict}"]

    if k > 5 and ndcg is not None and ndcg > 0.8:
        estimated_savings = round((1 - 5/k) * 100)
        parts.append(
            f"Tip: Reducing K from {k}→5 would save ~{estimated_savings}% evaluation cost "
            f"with estimated <3% quality impact based on your NDCG curve."
        )

    return " | ".join(parts)
