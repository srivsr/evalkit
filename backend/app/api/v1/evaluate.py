import time
import uuid
import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import APIKey, Project, GatePolicy, Evaluation, EvaluationMetric, AutofixRecommendation
from ...schemas import (
    EvaluateRequest,
    EvaluateResponse,
    MetricsResponse,
    BatchEvaluateRequest,
    BatchEvaluateResponse,
    AutofixResponse,
    AutofixRecommendationResponse,
)
from ...security import require_scope
from ...cache import evaluation_cache
from ...core import (
    MultiStageEvaluationPipeline,
    GatePolicyEngine,
    AutoFixEngine,
    normalize_api_request,
)
from ...utils import generate_cache_key
from ...cost import CostCalculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["evaluate"])

pipeline = MultiStageEvaluationPipeline()
gate_engine = GatePolicyEngine()
autofix_engine = AutoFixEngine()
cost_calculator = CostCalculator()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    request: EvaluateRequest,
    api_key: APIKey = Depends(require_scope("evaluate:write")),
    db: AsyncSession = Depends(get_db)
):
    """
    Run RAG evaluation.

    Accepts:
    - context: List[str] (simple format)
    - context_chunks: List[ContextChunk] (rich format with rank/score)

    Returns:
    - evaluation_id, metrics, decision, failure_codes, cost
    """
    start_time = time.time()

    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.organization_id == api_key.organization_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get gate policy
    policy_result = await db.execute(
        select(GatePolicy).where(GatePolicy.project_id == project.id)
    )
    policy = policy_result.scalar_one_or_none()
    policy_version = policy.version if policy else 1

    # Normalize request to canonical format
    canonical = normalize_api_request(request)
    canonical.policy_version = policy_version

    # Generate cache key
    cache_key, input_hash, cache_namespace = generate_cache_key(
        query=canonical.query,
        context_chunks=canonical.context_chunks,
        response=canonical.response,
        policy_version=policy_version,
        judge_model=canonical.judge_model,
        evaluator_version=canonical.evaluator_version
    )

    # Check cache
    cached_result = await evaluation_cache.get(cache_key, db)
    if cached_result:
        logger.info(f"Cache hit for evaluation")
        cached_result["cached"] = True
        # Convert metrics dict back to MetricsResponse if needed
        if isinstance(cached_result.get("metrics"), dict):
            cached_result["metrics"] = MetricsResponse(**cached_result["metrics"])
        return EvaluateResponse(**cached_result)

    # Run multi-stage pipeline
    logger.info(f"Running evaluation pipeline")
    pipeline_result = await pipeline.evaluate(canonical)

    # Apply gate policy
    decision, severity, failure_codes = gate_engine.evaluate(
        metrics=pipeline_result.metrics,
        policy=policy,
        issues=pipeline_result.issues
    )

    duration_ms = int((time.time() - start_time) * 1000)

    # Calculate cost
    context_texts = [c.text for c in canonical.context_chunks]
    cost_estimate = cost_calculator.estimate_evaluation_cost(
        query=canonical.query,
        context_texts=context_texts,
        response=canonical.response,
        pipeline_stage=pipeline_result.stage,
        judge_model=canonical.judge_model
    )

    # Store evaluation
    evaluation = Evaluation(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=api_key.organization_id,
        query=canonical.query,
        response=canonical.response,
        ground_truth=canonical.ground_truth,
        context=[c.model_dump() for c in canonical.context_chunks],
        eval_metadata=canonical.metadata,
        framework=canonical.framework,
        cache_namespace=cache_namespace,
        input_hash=input_hash,
        cached=False,
        pipeline_stage=pipeline_result.stage,
        decision=decision,
        failure_codes=failure_codes,
        total_cost=Decimal(str(cost_estimate["total_cost"])),
        tokens_used=pipeline_result.tokens_used,
        duration_ms=duration_ms,
        retrieval_latency_ms=canonical.retrieval_latency_ms,
        generation_latency_ms=canonical.generation_latency_ms,
    )
    db.add(evaluation)

    # Store metrics
    metrics = pipeline_result.metrics
    eval_metric = EvaluationMetric(
        evaluation_id=evaluation.id,
        faithfulness=Decimal(str(metrics.get("faithfulness"))) if metrics.get("faithfulness") is not None else None,
        answer_relevancy=Decimal(str(metrics.get("answer_relevancy"))) if metrics.get("answer_relevancy") is not None else None,
        context_precision=Decimal(str(metrics.get("context_precision"))) if metrics.get("context_precision") is not None else None,
        context_recall=Decimal(str(metrics.get("context_recall"))) if metrics.get("context_recall") is not None else None,
        hallucination_score=Decimal(str(metrics.get("hallucination_score"))) if metrics.get("hallucination_score") is not None else None,
        response_latency_ms=metrics.get("response_latency_ms"),
        cost_per_query=Decimal(str(cost_estimate["total_cost"])),
        severity=severity,
        confidence_score=Decimal(str(pipeline_result.confidence)),
    )
    db.add(eval_metric)

    # Generate AutoFix recommendations
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

    # Build response
    metrics_response = MetricsResponse(
        faithfulness=eval_metric.faithfulness,
        answer_relevancy=eval_metric.answer_relevancy,
        context_precision=eval_metric.context_precision,
        context_recall=eval_metric.context_recall,
        hallucination_score=eval_metric.hallucination_score,
        response_latency_ms=eval_metric.response_latency_ms,
        cost_per_query=eval_metric.cost_per_query,
    )

    response_data = {
        "evaluation_id": evaluation.id,
        "metrics": metrics_response,
        "decision": decision,
        "severity": severity,
        "failure_codes": failure_codes,
        "pipeline_stage": pipeline_result.stage,
        "cached": False,
        "cost": evaluation.total_cost,
        "duration_ms": duration_ms,
        "tokens_used": pipeline_result.tokens_used,
        "autofix_available": len(recommendations) > 0,
    }

    # Cache result (convert to dict for JSON serialization)
    cache_data = {
        **response_data,
        "evaluation_id": str(evaluation.id),
        "metrics": metrics_response.model_dump(),
        "cost": str(evaluation.total_cost),
    }
    await evaluation_cache.set(cache_key, cache_data, db)

    logger.info(f"Evaluation complete: {evaluation.id} (stage: {pipeline_result.stage}, decision: {decision})")

    return EvaluateResponse(**response_data)


@router.get("/evaluations/{evaluation_id}/autofix", response_model=AutofixResponse)
async def get_autofix(
    evaluation_id: uuid.UUID,
    api_key: APIKey = Depends(require_scope("evaluate:write")),
    db: AsyncSession = Depends(get_db)
):
    """Get AutoFix recommendations for an evaluation."""
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
    """Queue batch evaluation (async processing)."""
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    # TODO: Queue batch job for background processing

    return BatchEvaluateResponse(
        batch_id=batch_id,
        status="processing",
        total_count=len(request.evaluations),
        estimated_completion_seconds=len(request.evaluations) // 2 + 1
    )
