from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from ..models import GatePolicy


class GatePolicyEngine:
    def evaluate(
        self,
        metrics: Dict,
        policy: Optional[GatePolicy] = None,
        issues: List[Dict] = None
    ) -> Tuple[str, str, List[str]]:
        failure_codes = []
        severity = "P3"

        if issues:
            for issue in issues:
                failure_codes.append(issue["code"])
                if issue["severity"] == "P0":
                    severity = "P0"
                elif issue["severity"] == "P1" and severity not in ["P0"]:
                    severity = "P1"
                elif issue["severity"] == "P2" and severity not in ["P0", "P1"]:
                    severity = "P2"

        if policy:
            faithfulness = metrics.get("faithfulness")
            if faithfulness is not None and Decimal(str(faithfulness)) < policy.min_faithfulness:
                failure_codes.append("LOW_FAITHFULNESS")
                if Decimal(str(faithfulness)) < Decimal("0.5"):
                    severity = "P1" if severity not in ["P0"] else severity
                else:
                    severity = "P2" if severity not in ["P0", "P1"] else severity

            context_recall = metrics.get("context_recall")
            if context_recall is not None and Decimal(str(context_recall)) < policy.min_context_recall:
                failure_codes.append("LOW_RECALL")
                severity = "P2" if severity not in ["P0", "P1"] else severity

            context_precision = metrics.get("context_precision")
            if context_precision is not None and Decimal(str(context_precision)) < policy.min_context_precision:
                failure_codes.append("LOW_PRECISION")
                severity = "P2" if severity not in ["P0", "P1"] else severity

            hallucination = metrics.get("hallucination_score")
            if hallucination is not None and Decimal(str(hallucination)) > policy.max_hallucination:
                failure_codes.append("HALLUCINATION")
                if Decimal(str(hallucination)) > Decimal("0.4"):
                    severity = "P1" if severity not in ["P0"] else severity
                else:
                    severity = "P2" if severity not in ["P0", "P1"] else severity

            latency = metrics.get("response_latency_ms")
            if latency is not None and latency > policy.max_latency_ms:
                failure_codes.append("TOO_SLOW")
                severity = "P2" if severity not in ["P0", "P1"] else severity

            cost = metrics.get("cost_per_query")
            if cost is not None and Decimal(str(cost)) > policy.max_cost_per_query:
                failure_codes.append("TOO_EXPENSIVE")
                severity = "P2" if severity not in ["P0", "P1"] else severity

        if severity == "P0":
            decision = "fail"
        elif severity == "P1":
            decision = "fail"
        elif failure_codes:
            decision = "warn"
        else:
            decision = "pass"

        return decision, severity, failure_codes
