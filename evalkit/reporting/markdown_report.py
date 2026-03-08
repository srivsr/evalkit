"""Markdown report output — human-readable evaluation report."""


def generate_markdown_report(evaluation: dict) -> str:
    lines = []

    summary = evaluation.get("summary", {})
    root_cause = evaluation.get("root_cause", {})

    lines.append(f"# EvalKit Evaluation Report")
    lines.append(f"")
    lines.append(f"**Run ID:** {evaluation.get('run_id', 'N/A')}")
    lines.append(f"**Project:** {evaluation.get('project_id', 'N/A')}")
    lines.append(f"**Date:** {evaluation.get('created_at', 'N/A')}")
    lines.append(f"")

    verdict = summary.get("verdict", "N/A")
    verdict_emoji = {"PASS": "\u2705", "FAIL": "\u274c", "WARN": "\u26a0\ufe0f"}.get(verdict, "\u2753")
    lines.append(f"## Verdict: {verdict_emoji} {verdict}")
    lines.append(f"")
    lines.append(f"**Overall Score:** {summary.get('overall_score', 0):.2f}")
    lines.append(f"**Root Cause:** `{root_cause.get('code', 'N/A')}` ({root_cause.get('severity', 'N/A')})")
    lines.append(f"**Explanation:** {root_cause.get('message', 'N/A')}")
    lines.append(f"")

    ans = evaluation.get("answerability", {})
    lines.append(f"## Answerability")
    lines.append(f"")
    lines.append(f"**Classification:** {ans.get('classification', 'N/A')}")
    lines.append(f"**Rationale:** {ans.get('rationale', 'N/A')}")
    lines.append(f"")

    layer_a = evaluation.get("layer_a_retrieval", {})
    lines.append(f"## Retrieval Metrics (Layer A)")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    for metric in ["precision_at_k", "recall_at_k", "mrr", "ndcg_at_k", "hit_rate_at_k", "context_coverage"]:
        val = layer_a.get(metric)
        display = f"{val:.4f}" if val is not None else "N/A (no ground truth)"
        lines.append(f"| {metric} | {display} |")
    lines.append(f"")

    layer_b = evaluation.get("layer_b_generation", {})
    scores = layer_b.get("scores", {})
    lines.append(f"## Generation Metrics (Layer B)")
    lines.append(f"")
    lines.append(f"**Judge Model:** {layer_b.get('judge_model', 'N/A')}")
    lines.append(f"")
    lines.append(f"| Metric | Score |")
    lines.append(f"|--------|-------|")
    for metric in ["faithfulness", "answer_relevance"]:
        val = scores.get(metric)
        display = f"{val:.4f}" if val is not None else "N/A (no judge configured)"
        lines.append(f"| {metric} | {display} |")
    lines.append(f"")

    layer_c = evaluation.get("layer_c_claims", {})
    claims = layer_c.get("claims", [])
    if claims:
        lines.append(f"## Claim Verification (Layer C)")
        lines.append(f"")
        lines.append(f"**Supported:** {layer_c.get('supported_pct', 0):.0%}")
        lines.append(f"**Unsupported Claims:** {', '.join(layer_c.get('unsupported_claims', [])) or 'None'}")
        lines.append(f"")
        lines.append(f"| Claim | Status | Evidence |")
        lines.append(f"|-------|--------|----------|")
        for claim in claims:
            status_emoji = {"supported": "\u2705", "partially_supported": "\u26a0\ufe0f", "unsupported": "\u274c"}.get(claim.get("support", ""), "\u2753")
            evidence_text = claim.get("evidence", [{}])[0].get("quote", "\u2014") if claim.get("evidence") else "\u2014"
            text_preview = claim.get("text", "")[:60] + "..." if len(claim.get("text", "")) > 60 else claim.get("text", "")
            lines.append(f"| {text_preview} | {status_emoji} {claim.get('support', '')} | {evidence_text[:40]}... |")
        lines.append(f"")

    anomalies = evaluation.get("anomalies", [])
    if anomalies:
        lines.append(f"## \u26a0\ufe0f Anomalies Detected")
        lines.append(f"")
        for a in anomalies:
            lines.append(f"- **{a.get('code', '')}** ({a.get('severity', '')}): {a.get('message', '')}")
        lines.append(f"")

    fixes = evaluation.get("fix_suggestions", [])
    if fixes:
        lines.append(f"## \U0001f527 Recommended Fixes")
        lines.append(f"")
        for i, fix in enumerate(fixes, 1):
            priority_emoji = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}.get(fix.get("priority", ""), "\u26aa")
            lines.append(f"{i}. {priority_emoji} **[{fix.get('target', '')}]** {fix.get('action', '')}")
            if fix.get("detail"):
                lines.append(f"   _{fix['detail']}_")
        lines.append(f"")

    telemetry = evaluation.get("telemetry", {})
    lines.append(f"## Telemetry")
    lines.append(f"")
    lines.append(f"- **Total Latency:** {telemetry.get('total_latency_ms', 0)}ms")
    lines.append(f"- **Layer A:** {telemetry.get('layer_a_ms', 0)}ms")
    lines.append(f"- **Layer B:** {telemetry.get('layer_b_ms', 0)}ms")
    lines.append(f"- **Layer C:** {telemetry.get('layer_c_ms', 0)}ms")
    lines.append(f"- **Tokens Used:** {telemetry.get('tokens_used', 0)}")
    lines.append(f"- **Estimated Cost:** ${telemetry.get('estimated_cost_usd', 0):.4f}")
    lines.append(f"")

    confidence = summary.get("confidence", {})
    lines.append(f"---")
    lines.append(f"_Confidence: {confidence.get('mode', 'N/A')} | Judges: {confidence.get('judge_count', 0)}_")

    return "\n".join(lines)
