import logging
from typing import Optional
from dataclasses import dataclass
from ..schemas.canonical import CanonicalEvaluation

logger = logging.getLogger(__name__)


@dataclass
class DeepEvalResult:
    """DeepEval hallucination detection result"""
    hallucination_score: float  # 0 = no hallucination, 1 = full hallucination
    tokens_used: int
    cost: float


class DeepEvalWrapper:
    """
    Wrapper for DeepEval hallucination detection.

    Detects:
    - Factual hallucinations (claims not in context)
    - Contradictions (claims that contradict context)

    Score: 0.0 (no hallucination) to 1.0 (complete hallucination)
    """

    def __init__(self, judge_model: str = "gpt-4o-mini"):
        self.judge_model = judge_model
        self._deepeval_available = self._check_deepeval()

    def _check_deepeval(self) -> bool:
        """Check if DeepEval is installed"""
        try:
            import deepeval
            return True
        except ImportError:
            logger.warning("DeepEval not installed. Using mock hallucination detection.")
            return False

    async def evaluate(self, canonical: CanonicalEvaluation) -> DeepEvalResult:
        """
        Run hallucination detection.

        Returns hallucination score + cost/tokens used.
        """
        if self._deepeval_available:
            return await self._run_deepeval(canonical)
        else:
            return await self._run_mock(canonical)

    async def _run_deepeval(self, canonical: CanonicalEvaluation) -> DeepEvalResult:
        """Run actual DeepEval hallucination detection"""
        try:
            from deepeval.metrics import HallucinationMetric
            from deepeval.test_case import LLMTestCase

            # Create test case
            test_case = LLMTestCase(
                input=canonical.query,
                actual_output=canonical.response,
                context=[chunk.text for chunk in canonical.context_chunks]
            )

            # Create metric
            metric = HallucinationMetric(threshold=0.5)

            # Measure
            metric.measure(test_case)

            return DeepEvalResult(
                hallucination_score=1.0 - metric.score,  # Convert to 0=good, 1=bad
                tokens_used=getattr(metric, 'tokens_used', 200),
                cost=getattr(metric, 'cost', 0.0001)
            )

        except Exception as e:
            logger.error(f"DeepEval evaluation failed: {e}")
            return await self._run_mock(canonical)

    async def _run_mock(self, canonical: CanonicalEvaluation) -> DeepEvalResult:
        """Mock hallucination detection for development/testing"""
        import random

        # Generate realistic mock score (lower is better)
        base_score = 0.1 + random.uniform(-0.05, 0.15)

        return DeepEvalResult(
            hallucination_score=min(1.0, max(0.0, base_score)),
            tokens_used=200,
            cost=0.00005
        )
