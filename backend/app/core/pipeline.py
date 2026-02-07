from typing import Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal
from ..schemas import CanonicalEvaluation
from ..utils import TokenCounter, CostCalculator
from ..config import get_settings

settings = get_settings()


@dataclass
class DeterministicResult:
    issues: List[Dict]
    metrics: Dict
    confidence: float

    def has_p0_failures(self) -> bool:
        return any(issue["severity"] == "P0" for issue in self.issues)


@dataclass
class ModelResult:
    metrics: Dict
    confidence: float
    cost: Decimal


class MultiStageEvaluationPipeline:
    def __init__(
        self,
        small_model: str = None,
        large_model: str = None,
        confidence_threshold: float = None
    ):
        self.small_model = small_model or settings.small_model
        self.large_model = large_model or settings.large_model
        self.confidence_threshold = confidence_threshold or settings.confidence_threshold
        self.token_counter = TokenCounter()
        self.cost_calculator = CostCalculator()

    async def evaluate(self, canonical: CanonicalEvaluation) -> Dict:
        deterministic = await self.stage_1_deterministic(canonical)

        if deterministic.has_p0_failures():
            return self._build_result(
                canonical=canonical,
                stage="deterministic",
                deterministic=deterministic,
                confidence=1.0
            )

        if deterministic.confidence >= self.confidence_threshold:
            return self._build_result(
                canonical=canonical,
                stage="deterministic",
                deterministic=deterministic,
                confidence=deterministic.confidence
            )

        small_model_result = await self.stage_2_small_model(canonical, deterministic)

        if small_model_result.confidence >= self.confidence_threshold:
            return self._build_result(
                canonical=canonical,
                stage="small_model",
                deterministic=deterministic,
                small_model=small_model_result,
                confidence=small_model_result.confidence
            )

        large_model_result = await self.stage_3_large_model(canonical)

        return self._build_result(
            canonical=canonical,
            stage="large_model",
            deterministic=deterministic,
            small_model=small_model_result,
            large_model=large_model_result,
            confidence=1.0
        )

    async def stage_1_deterministic(self, canonical: CanonicalEvaluation) -> DeterministicResult:
        issues = []
        metrics = {}

        if not canonical.response or len(canonical.response.strip()) < 10:
            issues.append({
                "code": "EMPTY_ANSWER",
                "severity": "P0",
                "message": "Response is empty or too short (<10 chars)"
            })

        if not canonical.context_chunks or all(
            len(chunk.text.strip()) < 10
            for chunk in canonical.context_chunks
        ):
            issues.append({
                "code": "NO_CONTEXT",
                "severity": "P0",
                "message": "No valid context chunks provided"
            })

        total_tokens = (
            self.token_counter.count(canonical.query) +
            sum(self.token_counter.count(c.text) for c in canonical.context_chunks) +
            self.token_counter.count(canonical.response)
        )

        if total_tokens > 128000:
            issues.append({
                "code": "TOKEN_LIMIT_EXCEEDED",
                "severity": "P1",
                "message": f"Total tokens ({total_tokens}) exceeds 128K limit"
            })

        metrics["response_latency_ms"] = canonical.total_latency_ms or 0
        metrics["total_tokens"] = total_tokens

        model = canonical.metadata.get("model", "gpt-4o")
        response_tokens = self.token_counter.count(canonical.response)
        cost = self.cost_calculator.calculate(
            model=model,
            input_tokens=total_tokens - response_tokens,
            output_tokens=response_tokens
        )
        metrics["cost_per_query"] = float(cost)

        confidence = 0.3 if issues else 0.6

        return DeterministicResult(
            issues=issues,
            metrics=metrics,
            confidence=confidence
        )

    async def stage_2_small_model(
        self,
        canonical: CanonicalEvaluation,
        deterministic: DeterministicResult
    ) -> ModelResult:
        metrics = await self._run_ragas(canonical, self.small_model)
        hallucination = await self._run_hallucination_check(canonical, self.small_model)
        metrics["hallucination_score"] = hallucination

        confidence = self._calculate_confidence(metrics)

        cost = self._calculate_stage_cost(canonical, self.small_model)

        return ModelResult(
            metrics=metrics,
            confidence=confidence,
            cost=cost
        )

    async def stage_3_large_model(self, canonical: CanonicalEvaluation) -> ModelResult:
        metrics = await self._run_ragas(canonical, self.large_model)
        hallucination = await self._run_hallucination_check(canonical, self.large_model)
        metrics["hallucination_score"] = hallucination

        cost = self._calculate_stage_cost(canonical, self.large_model)

        return ModelResult(
            metrics=metrics,
            confidence=1.0,
            cost=cost
        )

    async def _run_ragas(self, canonical: CanonicalEvaluation, model: str) -> Dict:
        return {
            "faithfulness": 0.85,
            "answer_relevancy": 0.82,
            "context_precision": 0.78,
            "context_recall": 0.75,
        }

    async def _run_hallucination_check(self, canonical: CanonicalEvaluation, model: str) -> float:
        return 0.12

    def _calculate_confidence(self, metrics: Dict) -> float:
        scores = [
            metrics.get("faithfulness", 0.5),
            metrics.get("answer_relevancy", 0.5),
            metrics.get("context_precision", 0.5),
            metrics.get("context_recall", 0.5)
        ]

        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)

        if variance < 0.05:
            return 0.9
        elif variance < 0.15:
            return 0.7
        return 0.4

    def _calculate_stage_cost(self, canonical: CanonicalEvaluation, model: str) -> Decimal:
        total_tokens = (
            self.token_counter.count(canonical.query) +
            sum(self.token_counter.count(c.text) for c in canonical.context_chunks) +
            self.token_counter.count(canonical.response)
        )
        return self.cost_calculator.calculate(model, total_tokens, 500)

    def _build_result(
        self,
        canonical: CanonicalEvaluation,
        stage: str,
        deterministic: DeterministicResult,
        small_model: Optional[ModelResult] = None,
        large_model: Optional[ModelResult] = None,
        confidence: float = 1.0
    ) -> Dict:
        if large_model:
            metrics = large_model.metrics
            total_cost = deterministic.metrics.get("cost_per_query", 0) + float(small_model.cost) + float(large_model.cost)
        elif small_model:
            metrics = small_model.metrics
            total_cost = deterministic.metrics.get("cost_per_query", 0) + float(small_model.cost)
        else:
            metrics = deterministic.metrics
            total_cost = deterministic.metrics.get("cost_per_query", 0)

        metrics.update({
            "response_latency_ms": deterministic.metrics.get("response_latency_ms"),
            "cost_per_query": deterministic.metrics.get("cost_per_query"),
        })

        return {
            "stage": stage,
            "metrics": metrics,
            "issues": deterministic.issues,
            "confidence": confidence,
            "total_cost": total_cost,
            "tokens_used": deterministic.metrics.get("total_tokens", 0),
        }
