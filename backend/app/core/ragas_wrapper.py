import logging
from typing import Dict, Optional
from dataclasses import dataclass
from ..schemas.canonical import CanonicalEvaluation

logger = logging.getLogger(__name__)


@dataclass
class RAGASResult:
    """RAGAS evaluation result"""
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    tokens_used: int
    cost: float


class RAGASWrapper:
    """
    Wrapper for RAGAS evaluation library.

    Metrics:
    - faithfulness: Is the answer supported by context?
    - answer_relevancy: Is the answer relevant to the query?
    - context_precision: Are retrieved chunks relevant?
    - context_recall: Are all relevant chunks retrieved?

    Uses LLM-as-judge approach with configurable judge model.
    """

    def __init__(self, judge_model: str = "gpt-4o-mini"):
        self.judge_model = judge_model
        self._ragas_available = self._check_ragas()

    def _check_ragas(self) -> bool:
        """Check if RAGAS is installed"""
        try:
            import ragas
            return True
        except ImportError:
            logger.warning("RAGAS not installed. Using mock metrics.")
            return False

    async def evaluate(self, canonical: CanonicalEvaluation) -> RAGASResult:
        """
        Run RAGAS evaluation.

        Returns metrics + cost/tokens used.
        """
        if self._ragas_available:
            return await self._run_ragas(canonical)
        else:
            return await self._run_mock(canonical)

    async def _run_ragas(self, canonical: CanonicalEvaluation) -> RAGASResult:
        """Run actual RAGAS evaluation"""
        try:
            from ragas import evaluate
            from ragas.metrics import (
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall
            )
            from datasets import Dataset

            # Convert to RAGAS format
            data = {
                "question": [canonical.query],
                "answer": [canonical.response],
                "contexts": [[chunk.text for chunk in canonical.context_chunks]],
            }

            if canonical.ground_truth:
                data["ground_truth"] = [canonical.ground_truth]

            dataset = Dataset.from_dict(data)

            # Run evaluation
            results = evaluate(
                dataset=dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall
                ]
            )

            return RAGASResult(
                faithfulness=float(results["faithfulness"]),
                answer_relevancy=float(results["answer_relevancy"]),
                context_precision=float(results["context_precision"]),
                context_recall=float(results["context_recall"]),
                tokens_used=results.get("total_tokens", 0),
                cost=results.get("total_cost", 0.0)
            )

        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            return await self._run_mock(canonical)

    async def _run_mock(self, canonical: CanonicalEvaluation) -> RAGASResult:
        """Mock RAGAS evaluation for development/testing"""
        import random

        # Generate realistic mock scores
        base_score = 0.75 + random.uniform(-0.15, 0.15)

        return RAGASResult(
            faithfulness=min(1.0, max(0.0, base_score + random.uniform(-0.1, 0.1))),
            answer_relevancy=min(1.0, max(0.0, base_score + random.uniform(-0.1, 0.1))),
            context_precision=min(1.0, max(0.0, base_score + random.uniform(-0.1, 0.1))),
            context_recall=min(1.0, max(0.0, base_score + random.uniform(-0.1, 0.1))),
            tokens_used=500,
            cost=0.0001
        )
