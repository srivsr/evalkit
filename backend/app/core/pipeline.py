import logging
from typing import Dict, Optional
from dataclasses import dataclass
from decimal import Decimal

from ..schemas.canonical import CanonicalEvaluation
from ..config import get_settings
from .deterministic import DeterministicChecker, DeterministicResult
from .ragas_wrapper import RAGASWrapper, RAGASResult
from .deepeval_wrapper import DeepEvalWrapper, DeepEvalResult
from .router import ConfidenceRouter

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class StageResult:
    """Result from a single pipeline stage"""
    metrics: Dict
    confidence: float
    cost: Decimal
    tokens_used: int


@dataclass
class PipelineResult:
    """Complete pipeline result"""
    stage: str
    metrics: Dict
    issues: list
    confidence: float
    total_cost: Decimal
    tokens_used: int


class MultiStageEvaluationPipeline:
    """
    Multi-Stage Evaluation Pipeline.

    Stage 1: Deterministic checks (FREE, 0 cost)
    - Empty response → P0 EMPTY_ANSWER
    - Empty context → P0 NO_CONTEXT
    - Token limit → P1 TOKEN_LIMIT_EXCEEDED
    - Expected: 60% complete here

    Stage 2: Small model (GPT-4o-mini, ~$0.15/M tokens)
    - RAGAS: faithfulness, answer_relevancy, context_precision, context_recall
    - DeepEval: hallucination_score
    - If confidence < 0.8 → escalate
    - Expected: 30% complete here

    Stage 3: Large model (GPT-4o, ~$5/M tokens)
    - Re-run with GPT-4o for better accuracy
    - Final stage, highest quality
    - Expected: 10% reach here

    Cost savings: 87-90% vs naive "always GPT-4o" approach
    """

    def __init__(
        self,
        small_model: str = None,
        large_model: str = None,
        confidence_threshold: float = None
    ):
        self.small_model = small_model or settings.small_model
        self.large_model = large_model or settings.large_model
        self.confidence_threshold = confidence_threshold or settings.confidence_threshold

        self.deterministic = DeterministicChecker()
        self.router = ConfidenceRouter(self.confidence_threshold)

    async def evaluate(self, canonical: CanonicalEvaluation) -> PipelineResult:
        """
        Run evaluation through multi-stage pipeline.

        Returns result from earliest stage with sufficient confidence.
        """
        # Stage 1: Deterministic checks (FREE)
        det_result = await self.stage_1_deterministic(canonical)

        # P0 failures stop immediately
        if det_result.has_p0_failures():
            logger.info(f"Stage 1: P0 failure detected, stopping")
            return PipelineResult(
                stage="deterministic",
                metrics=det_result.metrics,
                issues=det_result.issues,
                confidence=1.0,
                total_cost=Decimal("0"),
                tokens_used=det_result.metrics.get("total_tokens", 0)
            )

        # Check if we need Stage 2
        routing = self.router.should_escalate(
            det_result.metrics,
            "deterministic",
            det_result.confidence
        )

        if not routing.should_escalate:
            logger.info(f"Stage 1: High confidence ({det_result.confidence}), stopping")
            return PipelineResult(
                stage="deterministic",
                metrics=det_result.metrics,
                issues=det_result.issues,
                confidence=det_result.confidence,
                total_cost=Decimal("0"),
                tokens_used=det_result.metrics.get("total_tokens", 0)
            )

        # Stage 2: Small model evaluation
        logger.info(f"Escalating to Stage 2 (small model)")
        stage2_result = await self.stage_2_small_model(canonical)

        # Merge with deterministic metrics
        merged_metrics = {**det_result.metrics, **stage2_result.metrics}

        # Check if we need Stage 3
        routing = self.router.should_escalate(
            merged_metrics,
            "small_model",
            stage2_result.confidence
        )

        if not routing.should_escalate:
            logger.info(f"Stage 2: High confidence ({stage2_result.confidence}), stopping")
            return PipelineResult(
                stage="small_model",
                metrics=merged_metrics,
                issues=det_result.issues,
                confidence=stage2_result.confidence,
                total_cost=stage2_result.cost,
                tokens_used=det_result.metrics.get("total_tokens", 0) + stage2_result.tokens_used
            )

        # Stage 3: Large model evaluation
        logger.info(f"Escalating to Stage 3 (large model)")
        stage3_result = await self.stage_3_large_model(canonical)

        # Final metrics from large model
        final_metrics = {**det_result.metrics, **stage3_result.metrics}

        return PipelineResult(
            stage="large_model",
            metrics=final_metrics,
            issues=det_result.issues,
            confidence=1.0,
            total_cost=stage2_result.cost + stage3_result.cost,
            tokens_used=(
                det_result.metrics.get("total_tokens", 0) +
                stage2_result.tokens_used +
                stage3_result.tokens_used
            )
        )

    async def stage_1_deterministic(
        self,
        canonical: CanonicalEvaluation
    ) -> DeterministicResult:
        """Stage 1: Free deterministic checks"""
        return await self.deterministic.check(canonical)

    async def stage_2_small_model(
        self,
        canonical: CanonicalEvaluation
    ) -> StageResult:
        """Stage 2: Small model (GPT-4o-mini) evaluation"""
        # Run RAGAS metrics
        ragas = RAGASWrapper(judge_model=self.small_model)
        ragas_result = await ragas.evaluate(canonical)

        # Run DeepEval hallucination
        deepeval = DeepEvalWrapper(judge_model=self.small_model)
        deepeval_result = await deepeval.evaluate(canonical)

        # Combine metrics
        metrics = {
            "faithfulness": ragas_result.faithfulness,
            "answer_relevancy": ragas_result.answer_relevancy,
            "context_precision": ragas_result.context_precision,
            "context_recall": ragas_result.context_recall,
            "hallucination_score": deepeval_result.hallucination_score,
        }

        # Calculate confidence
        confidence = self.router.calculate_confidence(metrics)

        # Calculate total cost
        total_cost = Decimal(str(ragas_result.cost + deepeval_result.cost))
        total_tokens = ragas_result.tokens_used + deepeval_result.tokens_used

        return StageResult(
            metrics=metrics,
            confidence=confidence,
            cost=total_cost,
            tokens_used=total_tokens
        )

    async def stage_3_large_model(
        self,
        canonical: CanonicalEvaluation
    ) -> StageResult:
        """Stage 3: Large model (GPT-4o) evaluation"""
        # Run RAGAS metrics with large model
        ragas = RAGASWrapper(judge_model=self.large_model)
        ragas_result = await ragas.evaluate(canonical)

        # Run DeepEval with large model
        deepeval = DeepEvalWrapper(judge_model=self.large_model)
        deepeval_result = await deepeval.evaluate(canonical)

        # Combine metrics
        metrics = {
            "faithfulness": ragas_result.faithfulness,
            "answer_relevancy": ragas_result.answer_relevancy,
            "context_precision": ragas_result.context_precision,
            "context_recall": ragas_result.context_recall,
            "hallucination_score": deepeval_result.hallucination_score,
        }

        total_cost = Decimal(str(ragas_result.cost + deepeval_result.cost))
        total_tokens = ragas_result.tokens_used + deepeval_result.tokens_used

        return StageResult(
            metrics=metrics,
            confidence=1.0,  # Large model is always high confidence
            cost=total_cost,
            tokens_used=total_tokens
        )
