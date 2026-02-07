import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import APIKey, Project, GatePolicy, Evaluation, EvaluationMetric
from ..security import require_scope
from ..schemas import AnalyticsResponse, MetricsResponse

router = APIRouter(prefix="/v1", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    created_at: datetime


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    api_key: APIKey = Depends(require_scope("projects:read")),
    db: AsyncSession = Depends(get_db)
):
    project = Project(
        name=request.name,
        slug=request.slug,
        description=request.description,
        organization_id=api_key.organization_id,
    )
    db.add(project)

    policy = GatePolicy(project_id=project.id)
    db.add(policy)

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        created_at=project.created_at,
    )


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    api_key: APIKey = Depends(require_scope("projects:read")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project).where(Project.organization_id == api_key.organization_id)
    )
    projects = result.scalars().all()

    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.get("/projects/{project_id}/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    project_id: uuid.UUID,
    api_key: APIKey = Depends(require_scope("projects:read")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == api_key.organization_id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    count_result = await db.execute(
        select(func.count(Evaluation.id)).where(
            Evaluation.project_id == project_id,
            Evaluation.created_at >= thirty_days_ago
        )
    )
    total_evaluations = count_result.scalar() or 0

    avg_result = await db.execute(
        select(
            func.avg(EvaluationMetric.faithfulness),
            func.avg(EvaluationMetric.answer_relevancy),
            func.avg(EvaluationMetric.context_precision),
            func.avg(EvaluationMetric.context_recall),
            func.avg(EvaluationMetric.hallucination_score),
        ).join(Evaluation).where(
            Evaluation.project_id == project_id,
            Evaluation.created_at >= thirty_days_ago
        )
    )
    avg_metrics = avg_result.one()

    decision_result = await db.execute(
        select(Evaluation.decision, func.count(Evaluation.id)).where(
            Evaluation.project_id == project_id,
            Evaluation.created_at >= thirty_days_ago
        ).group_by(Evaluation.decision)
    )
    decision_distribution = {row[0]: row[1] for row in decision_result.all() if row[0]}

    severity_result = await db.execute(
        select(EvaluationMetric.severity, func.count(EvaluationMetric.id)).join(Evaluation).where(
            Evaluation.project_id == project_id,
            Evaluation.created_at >= thirty_days_ago
        ).group_by(EvaluationMetric.severity)
    )
    severity_distribution = {row[0]: row[1] for row in severity_result.all() if row[0]}

    cost_result = await db.execute(
        select(func.sum(Evaluation.total_cost)).where(
            Evaluation.project_id == project_id,
            Evaluation.created_at >= thirty_days_ago
        )
    )
    total_cost = cost_result.scalar() or Decimal("0")

    return AnalyticsResponse(
        period="last_30_days",
        total_evaluations=total_evaluations,
        average_metrics=MetricsResponse(
            faithfulness=Decimal(str(avg_metrics[0])) if avg_metrics[0] else None,
            answer_relevancy=Decimal(str(avg_metrics[1])) if avg_metrics[1] else None,
            context_precision=Decimal(str(avg_metrics[2])) if avg_metrics[2] else None,
            context_recall=Decimal(str(avg_metrics[3])) if avg_metrics[3] else None,
            hallucination_score=Decimal(str(avg_metrics[4])) if avg_metrics[4] else None,
        ),
        decision_distribution=decision_distribution,
        severity_distribution=severity_distribution,
        total_cost=total_cost,
        cost_savings={
            "total_savings": float(total_cost) * 8.7,
            "savings_percentage": 87.0,
            "disclaimer": "Based on estimated pipeline distribution",
        },
        trends={
            "faithfulness": [],
            "dates": [],
        },
        top_failure_codes=[],
    )
