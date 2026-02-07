import time
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import APIKey, Project, GatePolicy, Evaluation, EvaluationMetric, AutofixRecommendation
from ..schemas import (
    EvaluateRequest, EvaluateResponse, MetricsResponse,
    AutofixResponse, AutofixRecommendationResponse,
    BatchEvaluateRequest, BatchEvaluateResponse
)
from ..security import require_scope
from ..cache import evaluation_cache
from ..core import MultiStageEvaluationPipeline, GatePolicyEngine, AutoFixEngine, normalize_request
from ..utils import generate_cache_key

router = APIRouter(prefix="/v1", tags=["evaluate"])

pipeline = MultiStageEvaluationPipeline()
gate_engine = GatePolicyEngine()
autofix_engine = AutoFixEngine()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    request: EvaluateRequest,
    api_key: APIKey = Depends(require_scope("evaluate:write")),
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()

    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.organization_id == api_key.organization_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    policy_result = await db.execute(
        select(GatePolicy).where(GatePolicy.project_id == project.id)
    )
    policy = policy_result.scalar_one_or_none()
    policy_version = policy.version if policy else 1

    canonical = normalize_request(request)

    cache_key, input_hash, cache_namespace = generate_cache_key(
        query=canonical.query,
        context_chunks=canonical.context_chunks,
        response=canonical.response,
        policy_version=policy_version
    )

    cached_result = await evaluation_cache.get(cache_key, db)
    if cached_result:
        cached_result["cached"] = True
        return EvaluateResponse(**cached_result)

    eval_result = await pipeline.evaluate(canonical)

    decision, severity, failure_codes = gate_engine.evaluate(
        metrics=eval_result["metrics"],
        policy=policy,
        issues=eval_result["issues"]
    )

    duration_ms = int((time.time() - start_time) * 1000)

    evaluation = Evaluation(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=api_key.organization_id,
        query=canonical.query,
        response=canonical.response,
        ground_truth=canonical.ground_truth,
        context=[c.model_dump() for c in canonical.context_chunks],
        eval_metadata=canonical.metadata,
        framework=canonical.metadata.get("framework") if canonical.metadata else None,
        cache_namespace=cache_namespace,
        input_hash=input_hash,
        cached=False,
        pipeline_stage=eval_result["stage"],
        decision=decision,
        failure_codes=failure_codes,
        total_cost=Decimal(str(eval_result["total_cost"])),
        tokens_used=eval_result["tokens_used"],
        duration_ms=duration_ms,
        retrieval_latency_ms=canonical.retrieval_latency_ms,
        generation_latency_ms=canonical.generation_latency_ms,
    )
    db.add(evaluation)

    metrics = eval_result["metrics"]
    eval_metric = EvaluationMetric(
        evaluation_id=evaluation.id,
        faithfulness=Decimal(str(metrics.get("faithfulness"))) if metrics.get("faithfulness") else None,
        answer_relevancy=Decimal(str(metrics.get("answer_relevancy"))) if metrics.get("answer_relevancy") else None,
        context_precision=Decimal(str(metrics.get("context_precision"))) if metrics.get("context_precision") else None,
        context_recall=Decimal(str(metrics.get("context_recall"))) if metrics.get("context_recall") else None,
        hallucination_score=Decimal(str(metrics.get("hallucination_score"))) if metrics.get("hallucination_score") else None,
        response_latency_ms=metrics.get("response_latency_ms"),
        cost_per_query=Decimal(str(metrics.get("cost_per_query"))) if metrics.get("cost_per_query") else None,
        severity=severity,
        confidence_score=Decimal(str(eval_result["confidence"])),
    )
    db.add(eval_metric)

    recommendations = autofix_engine.analyze(canonical, metrics)
    for rec in recommendations:
        autofix = AutofixRecommendation(
            evaluation_id=evaluation.id,
            project_id=project.id,
            rule_name=rec["rule_name"],
            recommendation_type=rec["type"],
            current_value=rec["current_value"],
            recommended_value=rec["recommended_value"],
            expected_improvement=rec["expected_improvement"],
            confidence=rec["confidence"],
            evidence=rec["evidence"],
        )
        db.add(autofix)

    await db.commit()

    response_data = {
        "evaluation_id": evaluation.id,
        "metrics": MetricsResponse(
            faithfulness=eval_metric.faithfulness,
            answer_relevancy=eval_metric.answer_relevancy,
            context_precision=eval_metric.context_precision,
            context_recall=eval_metric.context_recall,
            hallucination_score=eval_metric.hallucination_score,
            response_latency_ms=eval_metric.response_latency_ms,
            cost_per_query=eval_metric.cost_per_query,
        ),
        "decision": decision,
        "severity": severity,
        "failure_codes": failure_codes,
        "pipeline_stage": eval_result["stage"],
        "cached": False,
        "cost": evaluation.total_cost,
        "duration_ms": duration_ms,
        "tokens_used": eval_result["tokens_used"],
        "autofix_available": len(recommendations) > 0,
    }

    await evaluation_cache.set(cache_key, response_data, db)

    return EvaluateResponse(**response_data)


@router.get("/evaluations/{evaluation_id}/autofix", response_model=AutofixResponse)
async def get_autofix(
    evaluation_id: uuid.UUID,
    api_key: APIKey = Depends(require_scope("evaluate:write")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation or evaluation.organization_id != api_key.organization_id:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    rec_result = await db.execute(
        select(AutofixRecommendation).where(
            AutofixRecommendation.evaluation_id == evaluation_id
        )
    )
    recommendations = rec_result.scalars().all()

    return AutofixResponse(
        evaluation_id=evaluation_id,
        recommendations=[
            AutofixRecommendationResponse(
                id=rec.id,
                rule_name=rec.rule_name,
                type=rec.recommendation_type,
                current_value=rec.current_value,
                recommended_value=rec.recommended_value,
                expected_improvement=rec.expected_improvement,
                confidence=rec.confidence,
                evidence=rec.evidence or {},
                explanation=rec.explanation or ""
            )
            for rec in recommendations
        ]
    )


@router.post("/evaluations/batch", response_model=BatchEvaluateResponse)
async def batch_evaluate(
    request: BatchEvaluateRequest,
    api_key: APIKey = Depends(require_scope("evaluate:write")),
    db: AsyncSession = Depends(get_db)
):
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    return BatchEvaluateResponse(
        batch_id=batch_id,
        status="processing",
        total_count=len(request.evaluations),
        estimated_completion_seconds=len(request.evaluations) // 2 + 1
    )
