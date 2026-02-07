from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from ..models import GatePolicy


class GatePolicyEngine:
    """
    Gate Policy Engine.

    Evaluates metrics against thresholds and generates:
    - Decision: pass / fail / warn
    - Severity: P0 (critical) / P1 (high) / P2 (medium) / P3 (low)
    - Failure codes: EMPTY_ANSWER, LOW_FAITHFULNESS, etc.

    Failure Code Taxonomy:
    - EMPTY_ANSWER: Response is empty (P0)
    - NO_CONTEXT: No context provided (P0)
    - LOW_FAITHFULNESS: Below threshold (P1/P2)
    - LOW_RECALL: Context recall below threshold (P2)
    - LOW_PRECISION: Context precision below threshold (P2)
    - HALLUCINATION: Hallucination score above threshold (P1/P2)
    - ANSWER_NOT_SUPPORTED: Answer not grounded in context (P1)
    - CONTRADICTS_CONTEXT: Answer contradicts context (P0)
    - TOO_SLOW: Latency above threshold (P2)
    - TOO_EXPENSIVE: Cost above threshold (P2)
    - TOKEN_LIMIT_EXCEEDED: Token limit exceeded (P1)
    """

    def evaluate(
        self,
        metrics: Dict,
        policy: Optional[GatePolicy] = None,
        issues: List[Dict] = None
    ) -> Tuple[str, str, List[str]]:
        """
        Evaluate metrics against policy.

        Returns: (decision, severity, failure_codes)
        """
        failure_codes = []
        severity = "P3"

        # Process deterministic issues first
        if issues:
            for issue in issues:
                failure_codes.append(issue["code"])
                severity = self._upgrade_severity(severity, issue["severity"])

        # Check against policy thresholds
        if policy:
            # Faithfulness check
            faithfulness = metrics.get("faithfulness")
            if faithfulness is not None:
                faith_decimal = Decimal(str(faithfulness))
                if faith_decimal < policy.min_faithfulness:
                    failure_codes.append("LOW_FAITHFULNESS")
                    if faith_decimal < Decimal("0.5"):
                        severity = self._upgrade_severity(severity, "P1")
                    else:
                        severity = self._upgrade_severity(severity, "P2")

            # Context recall check
            context_recall = metrics.get("context_recall")
            if context_recall is not None:
                if Decimal(str(context_recall)) < policy.min_context_recall:
                    failure_codes.append("LOW_RECALL")
                    severity = self._upgrade_severity(severity, "P2")

            # Context precision check
            context_precision = metrics.get("context_precision")
            if context_precision is not None:
                if Decimal(str(context_precision)) < policy.min_context_precision:
                    failure_codes.append("LOW_PRECISION")
                    severity = self._upgrade_severity(severity, "P2")

            # Hallucination check
            hallucination = metrics.get("hallucination_score")
            if hallucination is not None:
                hall_decimal = Decimal(str(hallucination))
                if hall_decimal > policy.max_hallucination:
                    failure_codes.append("HALLUCINATION")
                    if hall_decimal > Decimal("0.4"):
                        severity = self._upgrade_severity(severity, "P1")
                    else:
                        severity = self._upgrade_severity(severity, "P2")

            # Latency check
            latency = metrics.get("response_latency_ms")
            if latency is not None and latency > policy.max_latency_ms:
                failure_codes.append("TOO_SLOW")
                severity = self._upgrade_severity(severity, "P2")

            # Cost check
            cost = metrics.get("cost_per_query")
            if cost is not None:
                if Decimal(str(cost)) > policy.max_cost_per_query:
                    failure_codes.append("TOO_EXPENSIVE")
                    severity = self._upgrade_severity(severity, "P2")

        # Determine decision based on severity
        if severity == "P0":
            decision = "fail"
        elif severity == "P1":
            decision = "fail"
        elif failure_codes:
            decision = "warn"
        else:
            decision = "pass"

        return decision, severity, failure_codes

    def _upgrade_severity(self, current: str, new: str) -> str:
        """Upgrade severity to more critical level"""
        severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        if severity_order.get(new, 3) < severity_order.get(current, 3):
            return new
        return current
