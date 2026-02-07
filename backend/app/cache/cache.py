import json
import logging
from typing import Optional
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import get_settings
from ..models import Evaluation
from ..schemas import EvaluateResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class EvaluationCache:
    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> Optional[redis.Redis]:
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.redis_url)
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._redis = None
        return self._redis

    async def get(
        self,
        cache_key: str,
        db: AsyncSession
    ) -> Optional[dict]:
        r = await self._get_redis()
        if r:
            try:
                cached = await r.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        input_hash = cache_key.split(":")[-1]
        result = await db.execute(
            select(Evaluation).where(Evaluation.input_hash == input_hash)
        )
        evaluation = result.scalar_one_or_none()

        if evaluation and evaluation.metrics:
            return self._evaluation_to_dict(evaluation)

        return None

    async def set(
        self,
        cache_key: str,
        result: dict,
        db: AsyncSession
    ) -> None:
        r = await self._get_redis()
        if r:
            try:
                await r.setex(
                    cache_key,
                    settings.redis_cache_ttl,
                    json.dumps(result, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

    def _evaluation_to_dict(self, evaluation: Evaluation) -> dict:
        return {
            "evaluation_id": str(evaluation.id),
            "metrics": {
                "faithfulness": float(evaluation.metrics.faithfulness) if evaluation.metrics.faithfulness else None,
                "answer_relevancy": float(evaluation.metrics.answer_relevancy) if evaluation.metrics.answer_relevancy else None,
                "context_precision": float(evaluation.metrics.context_precision) if evaluation.metrics.context_precision else None,
                "context_recall": float(evaluation.metrics.context_recall) if evaluation.metrics.context_recall else None,
                "hallucination_score": float(evaluation.metrics.hallucination_score) if evaluation.metrics.hallucination_score else None,
                "response_latency_ms": evaluation.metrics.response_latency_ms,
                "cost_per_query": float(evaluation.metrics.cost_per_query) if evaluation.metrics.cost_per_query else None,
            },
            "decision": evaluation.decision,
            "severity": evaluation.metrics.severity,
            "failure_codes": evaluation.failure_codes or [],
            "pipeline_stage": evaluation.pipeline_stage,
            "cached": True,
            "cost": 0,
            "duration_ms": 0,
            "tokens_used": 0,
            "autofix_available": bool(evaluation.autofix_recommendations),
        }


evaluation_cache = EvaluationCache()
