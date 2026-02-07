from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from decimal import Decimal
import httpx


@dataclass
class ContextChunk:
    text: str
    source_id: Optional[str] = None
    rank: Optional[int] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "source_id": self.source_id,
            "rank": self.rank,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class Metrics:
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    hallucination_score: Optional[float] = None
    response_latency_ms: Optional[int] = None
    cost_per_query: Optional[float] = None


@dataclass
class EvaluationResult:
    evaluation_id: str
    metrics: Metrics
    decision: str
    severity: Optional[str]
    failure_codes: List[str]
    pipeline_stage: str
    cached: bool
    cost: float
    duration_ms: int
    tokens_used: int
    autofix_available: bool


@dataclass
class AutofixRecommendation:
    id: str
    rule_name: str
    type: str
    current_value: Any
    recommended_value: Any
    expected_improvement: str
    confidence: str
    evidence: Dict[str, Any]
    explanation: str


@dataclass
class AutofixResult:
    evaluation_id: str
    recommendations: List[AutofixRecommendation]


class EvalClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.evalkit.dev"
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def evaluate(
        self,
        project_id: str,
        query: str,
        response: str,
        context: Optional[List[str]] = None,
        context_chunks: Optional[List[Dict]] = None,
        ground_truth: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        payload = {
            "project_id": project_id,
            "query": query,
            "response": response,
            "metadata": metadata or {},
        }

        if context_chunks:
            payload["context_chunks"] = context_chunks
        elif context:
            payload["context"] = context

        if ground_truth:
            payload["ground_truth"] = ground_truth

        resp = self._client.post(f"{self.base_url}/v1/evaluate", json=payload)
        resp.raise_for_status()
        data = resp.json()

        return EvaluationResult(
            evaluation_id=data["evaluation_id"],
            metrics=Metrics(
                faithfulness=data["metrics"].get("faithfulness"),
                answer_relevancy=data["metrics"].get("answer_relevancy"),
                context_precision=data["metrics"].get("context_precision"),
                context_recall=data["metrics"].get("context_recall"),
                hallucination_score=data["metrics"].get("hallucination_score"),
                response_latency_ms=data["metrics"].get("response_latency_ms"),
                cost_per_query=data["metrics"].get("cost_per_query"),
            ),
            decision=data["decision"],
            severity=data.get("severity"),
            failure_codes=data.get("failure_codes", []),
            pipeline_stage=data["pipeline_stage"],
            cached=data["cached"],
            cost=float(data["cost"]),
            duration_ms=data["duration_ms"],
            tokens_used=data["tokens_used"],
            autofix_available=data["autofix_available"],
        )

    def get_autofix(self, evaluation_id: str) -> AutofixResult:
        resp = self._client.get(f"{self.base_url}/v1/evaluations/{evaluation_id}/autofix")
        resp.raise_for_status()
        data = resp.json()

        return AutofixResult(
            evaluation_id=data["evaluation_id"],
            recommendations=[
                AutofixRecommendation(
                    id=rec["id"],
                    rule_name=rec["rule_name"],
                    type=rec["type"],
                    current_value=rec["current_value"],
                    recommended_value=rec["recommended_value"],
                    expected_improvement=rec["expected_improvement"],
                    confidence=rec["confidence"],
                    evidence=rec["evidence"],
                    explanation=rec["explanation"],
                )
                for rec in data["recommendations"]
            ],
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
