"""
Cross-Layer Anomaly Detection — from EVALKIT_MASTER_SPEC_v2.md Section 6.

5 Phase 1 rules that flag contradictory or suspicious metric combinations.
Each rule compares signals across layers to catch evaluation blind spots.
"""
from evalkit.config import settings


_ANOMALY_TO_ROOT_CAUSE = {
    "RETRIEVAL_OK_BUT_HALLUCINATING": {"HALLUCINATION", "GENERATION_UNFAITHFUL"},
    "SUSPICIOUS_FAITHFULNESS": {"HALLUCINATION"},
    "REGRESSION_DETECTED": set(),
}


def detect_anomalies(
    layer_a: dict,
    layer_b: dict,
    layer_c: dict,
    baseline: dict | None = None,
    root_cause_code: str | None = None,
) -> list[dict]:
    anomalies = []

    ndcg = layer_a.get("ndcg_at_k")
    recall = layer_a.get("recall_at_k")

    scores = layer_b.get("scores", {}) if isinstance(layer_b, dict) else {}
    faithfulness = scores.get("faithfulness")
    relevance = scores.get("answer_relevance")

    supported_pct = layer_c.get("supported_pct") if isinstance(layer_c, dict) else None

    # Rule 1: High Retrieval + Low Faithfulness
    if (ndcg is not None and faithfulness is not None
            and ndcg > 0.8 and faithfulness < 0.5):
        anomalies.append({
            "code": "RETRIEVAL_OK_BUT_HALLUCINATING",
            "severity": "critical",
            "message": f"Retrieval found good evidence (NDCG={ndcg:.2f}) but generation is unfaithful (faithfulness={faithfulness:.2f}). Check prompt template or model.",
        })

    # Rule 2: Low Retrieval + High Faithfulness
    if (recall is not None and faithfulness is not None
            and recall < 0.3 and faithfulness > 0.8):
        anomalies.append({
            "code": "SUSPICIOUS_FAITHFULNESS",
            "severity": "critical",
            "message": f"Retrieval is poor (Recall={recall:.2f}) but faithfulness is suspiciously high ({faithfulness:.2f}). Model may be hallucinating content that sounds grounded.",
        })

    # Rule 3: High Claim Support + Low Answer Relevance
    if (supported_pct is not None and relevance is not None
            and supported_pct > 0.8 and relevance < 0.5):
        anomalies.append({
            "code": "GROUNDED_BUT_OFF_TOPIC",
            "severity": "major",
            "message": f"Claims are well-supported ({supported_pct:.0%}) but answer doesn't address the query (relevance={relevance:.2f}). Check query understanding.",
        })

    # Rule 5: Regression — >20% drop from baseline
    if baseline is not None:
        regression_anomalies = _check_regression_anomaly(layer_a, layer_b, layer_c, baseline)
        anomalies.extend(regression_anomalies)

    if root_cause_code:
        anomalies = [
            a for a in anomalies
            if root_cause_code not in _ANOMALY_TO_ROOT_CAUSE.get(a["code"], set())
        ]

    return anomalies


def check_calibration_anomaly(
    layer_a: dict,
    layer_b: dict,
    layer_c: dict,
    user_verdict: str | None = None,
) -> dict | None:
    """Rule 4: All metrics high but user says FAIL."""
    if user_verdict != "FAIL":
        return None

    scores = layer_b.get("scores", {}) if isinstance(layer_b, dict) else {}
    faithfulness = scores.get("faithfulness")
    relevance = scores.get("answer_relevance")
    supported_pct = layer_c.get("supported_pct") if isinstance(layer_c, dict) else None
    recall = layer_a.get("recall_at_k")

    high_count = 0
    total = 0
    for val in [faithfulness, relevance, supported_pct, recall]:
        if val is not None:
            total += 1
            if val > 0.7:
                high_count += 1

    if total >= 2 and high_count == total:
        return {
            "code": "EVALUATION_CALIBRATION_ISSUE",
            "severity": "major",
            "message": "All available metrics score high but user marked as FAIL. Judges may be miscalibrated or evaluation criteria may need adjustment.",
        }

    return None


def _check_regression_anomaly(
    layer_a: dict,
    layer_b: dict,
    layer_c: dict,
    baseline: dict,
) -> list[dict]:
    """Rule 5: Flag any metric that dropped more than anomaly_regression_pct from baseline."""
    anomalies = []

    baseline_a = baseline.get("layer_a_retrieval", {})
    baseline_b_scores = baseline.get("layer_b_generation", {}).get("scores", {})
    baseline_c = baseline.get("layer_c_claims", {})

    current_b_scores = layer_b.get("scores", {}) if isinstance(layer_b, dict) else {}

    comparisons = [
        ("recall_at_k", layer_a.get("recall_at_k"), baseline_a.get("recall_at_k")),
        ("precision_at_k", layer_a.get("precision_at_k"), baseline_a.get("precision_at_k")),
        ("ndcg_at_k", layer_a.get("ndcg_at_k"), baseline_a.get("ndcg_at_k")),
        ("faithfulness", current_b_scores.get("faithfulness"), baseline_b_scores.get("faithfulness")),
        ("supported_pct", layer_c.get("supported_pct") if isinstance(layer_c, dict) else None, baseline_c.get("supported_pct")),
    ]

    for metric_name, current_val, baseline_val in comparisons:
        if current_val is not None and baseline_val is not None and baseline_val > 0:
            drop_pct = (baseline_val - current_val) / baseline_val
            if drop_pct > settings.thresholds.anomaly_regression_pct:
                anomalies.append({
                    "code": "REGRESSION_DETECTED",
                    "severity": "major",
                    "message": f"Metric '{metric_name}' dropped {drop_pct:.0%} from baseline ({baseline_val:.2f} → {current_val:.2f}). Something may have changed in the RAG pipeline.",
                })

    return anomalies
