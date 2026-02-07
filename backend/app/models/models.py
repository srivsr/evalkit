import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, ForeignKey,
    DECIMAL, ARRAY, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from ..database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan_type = Column(String(50), default="free")
    stripe_customer_id = Column(String(255))
    data_retention_days = Column(Integer, default=90)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    users = relationship("User", back_populates="organization")
    api_keys = relationship("APIKey", back_populates="organization")
    projects = relationship("Project", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    role = Column(String(50), default="member")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    organization = relationship("Organization", back_populates="users")

    __table_args__ = (
        Index("idx_users_clerk_id", "clerk_user_id"),
        Index("idx_users_org_id", "organization_id"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), unique=True, nullable=False)
    key_prefix = Column(String(10), nullable=False)
    name = Column(String(255), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    scopes = Column(JSONB, default=["evaluate:write", "projects:read"])
    rotated_from_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"))
    revoked = Column(Boolean, default=False)
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utc_now)
    expires_at = Column(DateTime(timezone=True))

    organization = relationship("Organization", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_hash", "key_hash"),
        Index("idx_api_keys_org", "organization_id"),
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    config = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    organization = relationship("Organization", back_populates="projects")
    gate_policy = relationship("GatePolicy", back_populates="project", uselist=False)
    evaluations = relationship("Evaluation", back_populates="project")

    __table_args__ = (
        UniqueConstraint("organization_id", "slug"),
        Index("idx_projects_org", "organization_id"),
        Index("idx_projects_config", "config", postgresql_using="gin"),
    )


class GatePolicy(Base):
    __tablename__ = "gate_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    min_faithfulness = Column(DECIMAL(5, 4), default=0.7000)
    min_context_recall = Column(DECIMAL(5, 4), default=0.6000)
    min_context_precision = Column(DECIMAL(5, 4), default=0.6000)
    max_hallucination = Column(DECIMAL(5, 4), default=0.2000)
    max_latency_ms = Column(Integer, default=5000)
    max_cost_per_query = Column(DECIMAL(10, 6), default=0.0100)
    p0_rules = Column(JSONB, default={"empty_answer": True, "no_context": True})
    p1_rules = Column(JSONB, default={"faithfulness": 0.5000, "hallucination": 0.4000})
    p2_rules = Column(JSONB, default={"faithfulness": 0.6000, "context_recall": 0.5000})
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="gate_policy")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    ground_truth = Column(Text)
    context = Column(JSONB, nullable=False)
    eval_metadata = Column(JSONB, default={})
    framework = Column(String(50))
    cache_namespace = Column(String(255))
    input_hash = Column(String(64))
    cached_from_evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id"))
    cached = Column(Boolean, default=False)
    pipeline_stage = Column(String(50))
    decision = Column(String(10))
    failure_codes = Column(ARRAY(Text))
    total_cost = Column(DECIMAL(10, 6), default=0.00)
    tokens_used = Column(Integer, default=0)
    duration_ms = Column(Integer)
    retrieval_latency_ms = Column(Integer)
    generation_latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    project = relationship("Project", back_populates="evaluations")
    metrics = relationship("EvaluationMetric", back_populates="evaluation", uselist=False)
    autofix_recommendations = relationship("AutofixRecommendation", back_populates="evaluation")

    __table_args__ = (
        Index("idx_evaluations_project", "project_id"),
        Index("idx_evaluations_org", "organization_id"),
        Index("idx_evaluations_created", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_evaluations_metadata", "eval_metadata", postgresql_using="gin"),
        Index("idx_evaluations_decision", "decision"),
        Index("idx_evaluations_failure_codes", "failure_codes", postgresql_using="gin"),
        Index("idx_eval_hash", "input_hash"),
    )


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"))
    faithfulness = Column(DECIMAL(5, 4))
    answer_relevancy = Column(DECIMAL(5, 4))
    context_precision = Column(DECIMAL(5, 4))
    context_recall = Column(DECIMAL(5, 4))
    hallucination_score = Column(DECIMAL(5, 4))
    response_latency_ms = Column(Integer)
    cost_per_query = Column(DECIMAL(10, 6))
    severity = Column(String(10))
    confidence_score = Column(DECIMAL(5, 4))
    created_at = Column(DateTime(timezone=True), default=utc_now)

    evaluation = relationship("Evaluation", back_populates="metrics")

    __table_args__ = (
        Index("idx_metrics_evaluation", "evaluation_id"),
        Index("idx_metrics_severity", "severity"),
    )


class AutofixRecommendation(Base):
    __tablename__ = "autofix_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    rule_name = Column(String(100), nullable=False)
    recommendation_type = Column(String(50))
    current_value = Column(JSONB)
    recommended_value = Column(JSONB)
    expected_improvement = Column(String(255))
    confidence = Column(String(50))
    evidence = Column(JSONB)
    explanation = Column(Text)
    applied = Column(Boolean, default=False)
    applied_at = Column(DateTime(timezone=True))
    feedback = Column(String(20))
    created_at = Column(DateTime(timezone=True), default=utc_now)

    evaluation = relationship("Evaluation", back_populates="autofix_recommendations")

    __table_args__ = (
        Index("idx_autofix_evaluation", "evaluation_id"),
        Index("idx_autofix_project", "project_id"),
        Index("idx_autofix_applied", "applied"),
        Index("idx_autofix_rule", "rule_name"),
    )


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    action_type = Column(String(50))
    quantity = Column(Integer, default=1)
    cost = Column(DECIMAL(10, 6), default=0.00)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("idx_usage_org", "organization_id"),
        Index("idx_usage_created", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_usage_org_date", "organization_id", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_usage_ratelimit", "organization_id", "action_type", "created_at", postgresql_ops={"created_at": "DESC"}),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    ip_address = Column(INET)
    user_agent = Column(Text)
    endpoint = Column(String(255))
    http_method = Column(String(10))
    action_type = Column(String(50))
    resource_type = Column(String(50))
    resource_id = Column(UUID(as_uuid=True))
    status_code = Column(Integer)
    error_message = Column(Text)
    request_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("idx_audit_org", "organization_id", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_audit_key", "api_key_id", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_audit_user", "user_id", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("idx_audit_request_id", "request_id"),
    )


class JobQueue(Base):
    __tablename__ = "job_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(20), default="pending")
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    worker_id = Column(String(100))

    __table_args__ = (
        Index("idx_job_status", "status", "priority", "created_at", postgresql_ops={"priority": "DESC", "created_at": "ASC"}),
        Index("idx_job_created", "created_at", postgresql_ops={"created_at": "DESC"}),
    )
