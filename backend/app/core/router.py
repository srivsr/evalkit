from typing import Dict
from dataclasses import dataclass


@dataclass
class RoutingDecision:
    """Routing decision for multi-stage pipeline"""
    should_escalate: bool
    reason: str
    confidence: float


class ConfidenceRouter:
    """
    Confidence-based routing for multi-stage pipeline.

    Routes evaluations based on confidence scores:
    - High confidence (>= 0.8): Stop at current stage
    - Low confidence (< 0.8): Escalate to next stage

    Expected distribution:
    - 60% complete at Stage 1 (deterministic)
    - 30% complete at Stage 2 (small model)
    - 10% require Stage 3 (large model)
    """

    DEFAULT_THRESHOLD = 0.80

    def __init__(self, confidence_threshold: float = None):
        self.threshold = confidence_threshold or self.DEFAULT_THRESHOLD

    def should_escalate(
        self,
        metrics: Dict,
        current_stage: str,
        confidence: float
    ) -> RoutingDecision:
        """
        Determine if evaluation should escalate to next stage.

        Args:
            metrics: Current metrics from this stage
            current_stage: "deterministic" or "small_model"
            confidence: Confidence score from current stage

        Returns:
            RoutingDecision with escalation decision
        """
        # Stage 1 (deterministic) → Stage 2 (small model)
        if current_stage == "deterministic":
            if confidence >= self.threshold:
                return RoutingDecision(
                    should_escalate=False,
                    reason="High confidence from deterministic checks",
                    confidence=confidence
                )

            return RoutingDecision(
                should_escalate=True,
                reason="Low confidence, escalating to small model",
                confidence=confidence
            )

        # Stage 2 (small model) → Stage 3 (large model)
        elif current_stage == "small_model":
            if confidence >= self.threshold:
                return RoutingDecision(
                    should_escalate=False,
                    reason="High confidence from small model",
                    confidence=confidence
                )

            # Check for metric disagreement
            if self._has_metric_disagreement(metrics):
                return RoutingDecision(
                    should_escalate=True,
                    reason="Metric disagreement detected, escalating to large model",
                    confidence=confidence
                )

            return RoutingDecision(
                should_escalate=True,
                reason="Low confidence, escalating to large model",
                confidence=confidence
            )

        # Stage 3 (large model) - final stage, no escalation
        return RoutingDecision(
            should_escalate=False,
            reason="Final stage reached",
            confidence=1.0
        )

    def _has_metric_disagreement(self, metrics: Dict) -> bool:
        """
        Check if metrics show significant disagreement.

        High variance between metrics suggests ambiguous result.
        """
        scores = [
            metrics.get("faithfulness", 0.5),
            metrics.get("answer_relevancy", 0.5),
            metrics.get("context_precision", 0.5),
            metrics.get("context_recall", 0.5)
        ]

        if not scores:
            return False

        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)

        # High variance (> 0.15) indicates disagreement
        return variance > 0.15

    def calculate_confidence(self, metrics: Dict) -> float:
        """
        Calculate confidence score from metrics.

        Based on:
        - Metric agreement (low variance = high confidence)
        - Metric extremity (very high/low scores = higher confidence)
        """
        scores = [
            metrics.get("faithfulness", 0.5),
            metrics.get("answer_relevancy", 0.5),
            metrics.get("context_precision", 0.5),
            metrics.get("context_recall", 0.5)
        ]

        if not scores:
            return 0.5

        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)

        # Low variance = high agreement = high confidence
        if variance < 0.05:
            confidence = 0.9
        elif variance < 0.10:
            confidence = 0.8
        elif variance < 0.15:
            confidence = 0.7
        else:
            confidence = 0.5

        # Boost confidence for extreme scores (very good or very bad)
        if mean > 0.9 or mean < 0.3:
            confidence = min(1.0, confidence + 0.1)

        return confidence
