"""
Regression Detection — from EVALKIT_MASTER_SPEC_v2.md Section 6 (Layer E).

Compares current evaluation metrics to baseline.
Flags regressions when any metric drops > configurable threshold (default: 10%).
"""


TRACKED_METRICS = [
    "faithfulness",
    "precision_at_k",
    "recall_at_k",
    "supported_pct",
    "ndcg_at_k",
    "hit_rate_at_k",
    "answer_relevance",
]


def detect_regression(
    current_result: dict,
    baseline_result: dict,
    threshold: float | None = None,
) -> list[dict]:
    if threshold is None:
        from evalkit.config import settings
        threshold = settings.thresholds.regression_pct
    regressions = []

    current_metrics = _extract_metrics(current_result)
    baseline_metrics = _extract_metrics(baseline_result)

    for metric in TRACKED_METRICS:
        current_val = current_metrics.get(metric)
        baseline_val = baseline_metrics.get(metric)

        if current_val is None or baseline_val is None:
            continue

        if baseline_val > 0:
            relative_drop = (baseline_val - current_val) / baseline_val
            if relative_drop > threshold:
                regressions.append({
                    "metric": metric,
                    "baseline": round(baseline_val, 4),
                    "current": round(current_val, 4),
                    "delta_pct": round((current_val - baseline_val) / baseline_val * 100, 1),
                })

    return regressions


def compute_comparison(result_a: dict, result_b: dict) -> dict:
    metrics_a = _extract_metrics(result_a)
    metrics_b = _extract_metrics(result_b)

    deltas = []
    regressions = []

    all_metrics = set(list(metrics_a.keys()) + list(metrics_b.keys()))

    for metric in sorted(all_metrics):
        val_a = metrics_a.get(metric)
        val_b = metrics_b.get(metric)

        delta = None
        delta_pct = None

        if val_a is not None and val_b is not None:
            delta = round(val_b - val_a, 4)
            if val_a > 0:
                delta_pct = round(delta / val_a * 100, 1)

        entry = {
            "metric": metric,
            "run_a_value": round(val_a, 4) if val_a is not None else None,
            "run_b_value": round(val_b, 4) if val_b is not None else None,
            "delta": delta,
            "delta_pct": delta_pct,
        }
        deltas.append(entry)

        if val_a is not None and val_b is not None and val_a > 0:
            from evalkit.config import settings as _s
            if (val_a - val_b) / val_a > _s.thresholds.regression_pct:
                regressions.append(entry)

    if regressions:
        verdict = "degraded"
    elif any(d["delta"] is not None and d["delta"] > 0.05 for d in deltas):
        verdict = "improved"
    else:
        verdict = "stable"

    return {
        "deltas": deltas,
        "regressions": regressions,
        "verdict": verdict,
    }


def _extract_metrics(result: dict) -> dict:
    metrics = {}

    layer_a = result.get("layer_a_retrieval", {})
    for key in ["precision_at_k", "recall_at_k", "mrr", "ndcg_at_k", "hit_rate_at_k", "context_coverage"]:
        val = layer_a.get(key)
        if val is not None:
            metrics[key] = val

    layer_b = result.get("layer_b_generation", {})
    scores = layer_b.get("scores", {})
    for key in ["faithfulness", "answer_relevance"]:
        val = scores.get(key)
        if val is not None:
            metrics[key] = val

    layer_c = result.get("layer_c_claims", {})
    val = layer_c.get("supported_pct")
    if val is not None:
        metrics["supported_pct"] = val

    return metrics
