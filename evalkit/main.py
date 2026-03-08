"""EvalKit FastAPI application — from EVALKIT_MASTER_SPEC_v2.md Section 9."""
import logging
import uuid
import json
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from evalkit.config import settings
from evalkit.auth import get_current_user_id, close_http_client
from evalkit.rate_limit import enforce_rate_limit, enforce_rate_limit_evaluate
from evalkit.payment import router as payment_router
from evalkit.legal import router as legal_router
from evalkit.api_keys import router as api_keys_router
from evalkit.subscriptions import enforce_quota, check_project_limit
from evalkit.models.request import (
    EvaluateRequest, ChunkEvalRequest, ProjectCreateRequest,
    EmbeddingFitnessRequest,
)
from evalkit.models.response import (
    EvaluateResponse, ChunkEvalResponse, ProjectResponse,
    CompareResponse, HealthResponse, ErrorResponse,
    EmbeddingFitnessResponse, TermPairResult,
    Summary, ConfidenceInfo, Answerability, RetrievalMetrics,
    GenerationMetrics, GenerationScores, ClaimVerification,
    RootCause, Telemetry, ChunkEvalSummary, ChunkIssue,
    Claim, EvidenceSpan, Anomaly, FixSuggestion, MetricDelta,
    HallucinationTierResult, HallucinationDetail,
)
from evalkit.models.enums import (
    Verdict, Severity, RootCauseCode, AnswerabilityClass, ChunkQuality
)
from evalkit.storage import sqlite as storage
from evalkit.layers.retrieval import compute_retrieval_metrics
from evalkit.layers.claims import decompose_claims, verify_claims, compute_context_coverage
from evalkit.layers.generation import evaluate_generation
from evalkit.layers.answerability import classify_answerability
from evalkit.layers.root_cause import determine_root_cause
from evalkit.layers.chunk_quality import evaluate_chunks as run_chunk_evaluation
from evalkit.layers.anomaly import detect_anomalies
from evalkit.layers.fix_suggestions import generate_fix_suggestions
from evalkit.layers.cost_tracker import estimate_evaluation_cost
from evalkit.regression.detector import compute_comparison
from evalkit.layers.embedding_fitness import evaluate_embedding_fitness
from evalkit.judges.hallucination_tier import run_hallucination_tiering
from evalkit.layers.generation import create_judges


# --- App lifecycle ---

_db: Optional[aiosqlite.Connection] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db
    _db = await storage.get_connection(settings.db_path)
    yield
    await close_http_client()
    if _db:
        await _db.close()


app = FastAPI(
    title="EvalKit",
    description="QA-Grade RAG Evaluation Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payment_router)
app.include_router(legal_router)
app.include_router(api_keys_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return _db


# --- Health ---

@app.get("/v1/health", response_model=HealthResponse)
async def health_check():
    db = get_db()
    try:
        await db.execute("SELECT 1")
        return HealthResponse(status="ok", version="0.1.0", db_connected=True)
    except Exception:
        return HealthResponse(status="degraded", version="0.1.0", db_connected=False)


# --- Projects ---

@app.post("/v1/projects", response_model=ProjectResponse, status_code=201)
async def create_project(req: ProjectCreateRequest, user_id: str = Depends(enforce_rate_limit)):
    db = get_db()
    await check_project_limit(user_id, db)
    project_id = str(uuid.uuid4())
    try:
        result = await storage.create_project(db, project_id, req.name)
        # Store user_id on the project
        await db.execute("UPDATE projects SET user_id = ? WHERE id = ?", (user_id, project_id))
        await db.commit()
        return ProjectResponse(**result)
    except Exception as e:
        logger.error(f"Project creation failed: {e}")
        raise HTTPException(status_code=500, detail="Project creation failed")


@app.get("/v1/projects", response_model=list[ProjectResponse])
async def list_projects(user_id: str = Depends(enforce_rate_limit)):
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM projects WHERE user_id = ? OR user_id IS NULL ORDER BY created_at DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [ProjectResponse(**dict(row)) for row in rows]


@app.get("/v1/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user_id: str = Depends(enforce_rate_limit)):
    db = get_db()
    project = await storage.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("user_id") and project["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**project)


# --- Evaluate (Week 3: full pipeline A → C → B → D.0 → D) ---

@app.post("/v1/evaluate", response_model=EvaluateResponse, status_code=200)
async def evaluate(req: EvaluateRequest, user_id: str = Depends(enforce_rate_limit_evaluate)):
    db = get_db()
    await enforce_quota(user_id, db)
    run_id = req.run_id or str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    start_time = time.time()

    # Validate project exists
    project = await storage.get_project(db, req.project_id)
    if project is None:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Project not found",
                code="INVALID_INPUT",
                detail=f"Project '{req.project_id}' does not exist."
            ).model_dump(),
        )

    context_texts = [ctx.text for ctx in req.contexts]

    # Layer A: Retrieval Metrics
    layer_a_start = time.time()
    context_ids = [ctx.id for ctx in req.contexts]
    retrieval_result = compute_retrieval_metrics(
        context_ids=context_ids,
        relevance_labels=req.config.relevance_labels,
        k=req.config.k,
    )
    layer_a_ms = int((time.time() - layer_a_start) * 1000)

    # Layer C: Claim Decomposition + Verification
    layer_c_start = time.time()
    claims = decompose_claims(req.response)
    claim_result = verify_claims(
        claims=claims,
        contexts=[ctx.model_dump() for ctx in req.contexts],
        query=req.query,
    )
    # Wire Context Coverage back to Layer A
    retrieval_result["context_coverage"] = compute_context_coverage(
        claim_result, len(req.contexts),
    )
    layer_c_ms = int((time.time() - layer_c_start) * 1000)

    # Layer B: Generation Eval via Judge
    layer_b_start = time.time()
    generation_result = await evaluate_generation(
        query=req.query,
        response=req.response,
        contexts=context_texts,
        judge_mode=req.config.judge_mode,
        judge_models=req.config.judge_models,
        timeout_ms=req.config.timeout_ms,
        cost_cap_usd=req.config.cost_cap_usd,
        confidence_threshold=req.config.confidence_threshold,
        escalation_models=req.config.escalation_models,
    )
    layer_b_ms = int((time.time() - layer_b_start) * 1000)

    # Hallucination Tiering (between Layer B and D.0)
    tier_judges = create_judges(req.config.judge_models)
    hallucination_tier_result = await run_hallucination_tiering(
        query=req.query,
        response=req.response,
        contexts=context_texts,
        claim_results=claim_result,
        generation_result=generation_result,
        judges=tier_judges,
        requested_tier=req.config.hallucination_tier,
        cost_cap_usd=req.config.cost_cap_usd,
    )

    # Layer D.0: Answerability
    answerability_result = classify_answerability(
        retrieval_metrics=retrieval_result,
        claim_results=claim_result,
    )

    # Layer D: Root Cause Cascade
    root_cause_result = determine_root_cause(
        query=req.query,
        response=req.response,
        contexts=[ctx.model_dump() for ctx in req.contexts],
        retrieval_metrics=retrieval_result,
        generation_metrics=generation_result,
        claim_results=claim_result,
        answerability=answerability_result,
        hallucination_tier=hallucination_tier_result,
        relevance_labels=req.config.relevance_labels,
    )

    # Anomaly Detection
    anomaly_results = detect_anomalies(
        layer_a=retrieval_result,
        layer_b=generation_result,
        layer_c=claim_result,
        baseline=None,
    )

    # Fix Suggestions
    fix_results = generate_fix_suggestions(
        root_cause_code=root_cause_result["code"],
        context={"k": req.config.k, "ndcg_at_k": retrieval_result.get("ndcg_at_k")},
    )

    # Cost Estimation (Layer F)
    cost_result = estimate_evaluation_cost(
        query=req.query,
        response=req.response,
        contexts=context_texts,
        judge_model=generation_result.get("judge_model"),
        judge_calls=2 if generation_result.get("judge_model") else 0,
    )

    # Determine verdict from root cause
    rc_code = root_cause_result["code"]
    if rc_code == "PASS":
        verdict = Verdict.PASS
        overall_score = 1.0
    elif root_cause_result["severity"] in ("blocker", "critical"):
        verdict = Verdict.FAIL
        overall_score = 0.0
    else:
        verdict = Verdict.WARN
        overall_score = 0.5

    # Confidence object from judge results
    judge_confidence = generation_result.get("confidence", {})
    confidence = ConfidenceInfo(
        mode=judge_confidence.get("mode", "single_judge"),
        judge_count=judge_confidence.get("judge_count", 0),
        agreement_pct=judge_confidence.get("agreement_pct"),
        escalated=judge_confidence.get("escalated", False),
        escalation_reason=judge_confidence.get("escalation_reason"),
    )

    total_ms = int((time.time() - start_time) * 1000)

    # Build claims for response
    response_claims = [
        Claim(
            claim_id=c["claim_id"],
            text=c["text"],
            support=c["support"],
            evidence=[EvidenceSpan(**e) for e in c.get("evidence", [])],
        )
        for c in claim_result.get("claims", [])
    ]

    # Build Response
    result = EvaluateResponse(
        project_id=req.project_id,
        run_id=run_id,
        created_at=created_at,
        summary=Summary(verdict=verdict, confidence=confidence, overall_score=overall_score),
        answerability=Answerability(
            classification=AnswerabilityClass(answerability_result["classification"]),
            rationale=answerability_result["rationale"],
            expected_behavior=answerability_result["expected_behavior"],
        ),
        layer_a_retrieval=RetrievalMetrics(
            precision_at_k=retrieval_result["precision_at_k"],
            recall_at_k=retrieval_result["recall_at_k"],
            mrr=retrieval_result["mrr"],
            ndcg_at_k=retrieval_result["ndcg_at_k"],
            hit_rate_at_k=retrieval_result["hit_rate_at_k"],
            context_coverage=retrieval_result["context_coverage"],
            k=retrieval_result["k"],
        ),
        layer_b_generation=GenerationMetrics(
            scores=GenerationScores(
                faithfulness=generation_result["scores"].get("faithfulness"),
                answer_relevance=generation_result["scores"].get("answer_relevance"),
            ),
            judge_model=generation_result.get("judge_model"),
            prompt_version=generation_result.get("prompt_version"),
        ),
        layer_c_claims=ClaimVerification(
            claims=response_claims,
            supported_pct=claim_result.get("supported_pct", 0.0),
            unsupported_claims=claim_result.get("unsupported_claims", []),
        ),
        root_cause=RootCause(
            code=RootCauseCode(root_cause_result["code"]),
            message=root_cause_result["message"],
            severity=Severity(root_cause_result["severity"]),
            attribution=root_cause_result["attribution"],
        ),
        secondary_root_cause=RootCause(
            code=RootCauseCode(root_cause_result["secondary"]["code"]),
            message=root_cause_result["secondary"]["message"],
            severity=Severity(root_cause_result["secondary"]["severity"]),
            attribution=root_cause_result["secondary"]["attribution"],
        ) if root_cause_result.get("secondary") else None,
        hallucination_tier=HallucinationTierResult(
            tier_used=hallucination_tier_result["tier_used"],
            score=hallucination_tier_result["score"],
            confidence=hallucination_tier_result["confidence"],
            confidence_interval=hallucination_tier_result["confidence_interval"],
            method=hallucination_tier_result["method"],
            detail=HallucinationDetail(**hallucination_tier_result["detail"]) if hallucination_tier_result.get("detail") else None,
            fallback_used=hallucination_tier_result["fallback_used"],
            fallback_reason=hallucination_tier_result.get("fallback_reason"),
        ),
        anomalies=[Anomaly(**a) for a in anomaly_results],
        fix_suggestions=[FixSuggestion(**f) for f in fix_results],
        telemetry=Telemetry(
            total_latency_ms=total_ms,
            layer_a_ms=layer_a_ms,
            layer_b_ms=layer_b_ms,
            layer_c_ms=layer_c_ms,
            estimated_cost_usd=cost_result["estimated_cost_usd"],
            tokens_used=cost_result["tokens_used"],
        ),
    )

    # Store in SQLite
    await storage.store_evaluation(
        db=db, run_id=run_id, project_id=req.project_id,
        query=req.query, response=req.response,
        result_json=result.model_dump_json(),
        verdict=result.summary.verdict.value,
        root_cause_code=result.root_cause.code.value,
        reference_answer=req.reference_answer,
        config_json=req.config.model_dump_json(),
        request_json=req.model_dump_json(),
        contexts=[ctx.model_dump() for ctx in req.contexts],
    )

    # Store judge calibration metrics
    await storage.store_judge_calibration(
        db=db,
        run_id=run_id,
        project_id=req.project_id,
        judge_model=generation_result.get("judge_model") or "none",
        faithfulness=generation_result["scores"].get("faithfulness"),
        answer_relevance=generation_result["scores"].get("answer_relevance"),
        agreement_pct=judge_confidence.get("agreement_pct"),
        judge_count=judge_confidence.get("judge_count", 0),
        escalated=judge_confidence.get("escalated", False),
        confidence_threshold=req.config.confidence_threshold,
    )

    return result


# --- Evaluate Chunks (Week 2: real D.1 logic) ---

@app.post("/v1/evaluate/chunks", response_model=ChunkEvalResponse)
async def evaluate_chunks(req: ChunkEvalRequest):
    result = run_chunk_evaluation(
        chunks=[chunk.model_dump() for chunk in req.chunks],
        sample_size=req.sample_size,
        domain=req.domain,
    )
    return ChunkEvalResponse(
        overall_quality=ChunkQuality(result["overall_quality"]),
        score=result["score"],
        issues=[ChunkIssue(**issue) for issue in result["issues"]],
        summary=ChunkEvalSummary(**result["summary"]),
    )


# --- Embedding Fitness (Layer D.2) ---

@app.post("/v1/evaluate/embeddings", response_model=EmbeddingFitnessResponse)
async def evaluate_embeddings(req: EmbeddingFitnessRequest):
    db = get_db()
    project = await storage.get_project(db, req.project_id)
    if project is None:
        raise HTTPException(status_code=422, detail=f"Project '{req.project_id}' not found")

    result = await evaluate_embedding_fitness(
        project_id=req.project_id,
        embedding_model=req.embedding_model,
        domain=req.domain,
        term_pairs=[p.model_dump() for p in req.term_pairs],
        similarity_threshold=req.similarity_threshold,
    )

    return EmbeddingFitnessResponse(
        project_id=result["project_id"],
        embedding_model=result["embedding_model"],
        domain=result["domain"],
        fitness_score=result["fitness_score"],
        total_pairs=result["total_pairs"],
        passed_pairs=result["passed_pairs"],
        failed_pairs=result["failed_pairs"],
        results=[TermPairResult(**r) for r in result["results"]],
        recommendations=result["recommendations"],
        root_cause=result["root_cause"],
    )


# --- Evaluations ---

@app.get("/v1/evaluations")
async def list_evaluations(
    project_id: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    user_id: str = Depends(enforce_rate_limit),
):
    db = get_db()
    evals = await storage.list_evaluations(db, project_id)
    reverse = order == "desc"
    evals_sorted = sorted(evals, key=lambda e: e["created_at"], reverse=reverse)
    paginated = evals_sorted[offset:offset + limit]
    return [
        {
            "run_id": e["run_id"],
            "project_id": e["project_id"],
            "created_at": e["created_at"],
            "verdict": e["verdict"],
            "root_cause_code": e["root_cause_code"],
        }
        for e in paginated
    ]


@app.get("/v1/evaluations/{run_id}")
async def get_evaluation(run_id: str, user_id: str = Depends(enforce_rate_limit)):
    db = get_db()
    evaluation = await storage.get_evaluation(db, run_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    project = await storage.get_project(db, evaluation["project_id"])
    if project and project.get("user_id") and project["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    result = json.loads(evaluation["result_json"])
    contexts = await storage.get_contexts_for_run(db, run_id)
    result["input"] = {
        "query": evaluation["query"],
        "response": evaluation["response"],
        "reference_answer": evaluation.get("reference_answer"),
        "contexts": [
            {"id": c["context_id"], "text": c["text"], "source": c.get("source")}
            for c in contexts
        ],
        "config": json.loads(evaluation["config_json"]) if evaluation.get("config_json") else None,
    }
    return result


# --- Baseline + Regression ---

@app.post("/v1/evaluations/{run_id}/baseline")
async def mark_baseline(run_id: str, user_id: str = Depends(enforce_rate_limit)):
    db = get_db()
    success = await storage.mark_as_baseline(db, run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"run_id": run_id, "is_baseline": True}


@app.get("/v1/projects/{project_id}/regressions")
async def list_regressions(project_id: str, user_id: str = Depends(enforce_rate_limit)):
    db = get_db()
    regressions = await storage.list_regressions(db, project_id)
    return regressions


@app.get("/v1/projects/{project_id}/judge-calibration")
async def get_judge_calibration(
    project_id: str,
    judge_model: Optional[str] = Query(None),
    user_id: str = Depends(enforce_rate_limit),
):
    db = get_db()
    project = await storage.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    stats = await storage.get_judge_calibration_stats(db, project_id, judge_model)
    return stats


@app.get("/v1/compare")
async def compare_runs(run_a: str = Query(...), run_b: str = Query(...), user_id: str = Depends(enforce_rate_limit)):
    db = get_db()
    eval_a = await storage.get_evaluation(db, run_a)
    eval_b = await storage.get_evaluation(db, run_b)

    if eval_a is None or eval_b is None:
        missing = run_a if eval_a is None else run_b
        raise HTTPException(status_code=404, detail=f"Evaluation '{missing}' not found")

    result_a = json.loads(eval_a["result_json"])
    result_b = json.loads(eval_b["result_json"])

    comparison = compute_comparison(result_a, result_b)

    return CompareResponse(
        run_a=run_a,
        run_b=run_b,
        deltas=[MetricDelta(**d) for d in comparison["deltas"]],
        regressions=[MetricDelta(**r) for r in comparison["regressions"]],
        verdict=comparison["verdict"],
    ).model_dump()
