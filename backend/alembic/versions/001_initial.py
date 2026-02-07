"""Initial migration with all tables

Revision ID: 001
Revises:
Create Date: 2026-02-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('plan_type', sa.String(50), default='free'),
        sa.Column('stripe_customer_id', sa.String(255)),
        sa.Column('data_retention_days', sa.Integer(), default=90),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('clerk_user_id', sa.String(255), unique=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('role', sa.String(50), default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_users_clerk_id', 'users', ['clerk_user_id'])
    op.create_index('idx_users_org_id', 'users', ['organization_id'])

    # API Keys
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('scopes', postgresql.JSONB, default=['evaluate:write', 'projects:read']),
        sa.Column('rotated_from_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id')),
        sa.Column('revoked', sa.Boolean(), default=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
    )
    op.create_index('idx_api_keys_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_keys_org', 'api_keys', ['organization_id'])

    # Projects
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_projects_org', 'projects', ['organization_id'])
    op.create_index('idx_projects_config', 'projects', ['config'], postgresql_using='gin')
    op.create_unique_constraint('uq_projects_org_slug', 'projects', ['organization_id', 'slug'])

    # Gate Policies
    op.create_table(
        'gate_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), unique=True),
        sa.Column('min_faithfulness', sa.DECIMAL(5, 4), default=0.7000),
        sa.Column('min_context_recall', sa.DECIMAL(5, 4), default=0.6000),
        sa.Column('min_context_precision', sa.DECIMAL(5, 4), default=0.6000),
        sa.Column('max_hallucination', sa.DECIMAL(5, 4), default=0.2000),
        sa.Column('max_latency_ms', sa.Integer(), default=5000),
        sa.Column('max_cost_per_query', sa.DECIMAL(10, 6), default=0.0100),
        sa.Column('p0_rules', postgresql.JSONB, default={'empty_answer': True, 'no_context': True}),
        sa.Column('p1_rules', postgresql.JSONB, default={'faithfulness': 0.5000, 'hallucination': 0.4000}),
        sa.Column('p2_rules', postgresql.JSONB, default={'faithfulness': 0.6000, 'context_recall': 0.5000}),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Evaluations
    op.create_table(
        'evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('ground_truth', sa.Text()),
        sa.Column('context', postgresql.JSONB, nullable=False),
        sa.Column('eval_metadata', postgresql.JSONB, default={}),
        sa.Column('framework', sa.String(50)),
        sa.Column('cache_namespace', sa.String(255)),
        sa.Column('input_hash', sa.String(64)),
        sa.Column('cached_from_evaluation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluations.id')),
        sa.Column('cached', sa.Boolean(), default=False),
        sa.Column('pipeline_stage', sa.String(50)),
        sa.Column('decision', sa.String(10)),
        sa.Column('failure_codes', postgresql.ARRAY(sa.Text())),
        sa.Column('total_cost', sa.DECIMAL(10, 6), default=0.00),
        sa.Column('tokens_used', sa.Integer(), default=0),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('retrieval_latency_ms', sa.Integer()),
        sa.Column('generation_latency_ms', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_evaluations_project', 'evaluations', ['project_id'])
    op.create_index('idx_evaluations_org', 'evaluations', ['organization_id'])
    op.create_index('idx_evaluations_created', 'evaluations', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_evaluations_metadata', 'evaluations', ['eval_metadata'], postgresql_using='gin')
    op.create_index('idx_evaluations_decision', 'evaluations', ['decision'])
    op.create_index('idx_evaluations_failure_codes', 'evaluations', ['failure_codes'], postgresql_using='gin')
    op.create_index('idx_eval_hash', 'evaluations', ['input_hash'])

    # Evaluation Metrics
    op.create_table(
        'evaluation_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('evaluation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluations.id', ondelete='CASCADE')),
        sa.Column('faithfulness', sa.DECIMAL(5, 4)),
        sa.Column('answer_relevancy', sa.DECIMAL(5, 4)),
        sa.Column('context_precision', sa.DECIMAL(5, 4)),
        sa.Column('context_recall', sa.DECIMAL(5, 4)),
        sa.Column('hallucination_score', sa.DECIMAL(5, 4)),
        sa.Column('response_latency_ms', sa.Integer()),
        sa.Column('cost_per_query', sa.DECIMAL(10, 6)),
        sa.Column('severity', sa.String(10)),
        sa.Column('confidence_score', sa.DECIMAL(5, 4)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_metrics_evaluation', 'evaluation_metrics', ['evaluation_id'])
    op.create_index('idx_metrics_severity', 'evaluation_metrics', ['severity'])

    # AutoFix Recommendations
    op.create_table(
        'autofix_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('evaluation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluations.id', ondelete='CASCADE')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE')),
        sa.Column('rule_name', sa.String(100), nullable=False),
        sa.Column('recommendation_type', sa.String(50)),
        sa.Column('current_value', postgresql.JSONB),
        sa.Column('recommended_value', postgresql.JSONB),
        sa.Column('expected_improvement', sa.String(255)),
        sa.Column('confidence', sa.String(50)),
        sa.Column('evidence', postgresql.JSONB),
        sa.Column('explanation', sa.Text()),
        sa.Column('applied', sa.Boolean(), default=False),
        sa.Column('applied_at', sa.DateTime(timezone=True)),
        sa.Column('feedback', sa.String(20)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_autofix_evaluation', 'autofix_recommendations', ['evaluation_id'])
    op.create_index('idx_autofix_project', 'autofix_recommendations', ['project_id'])
    op.create_index('idx_autofix_applied', 'autofix_recommendations', ['applied'])
    op.create_index('idx_autofix_rule', 'autofix_recommendations', ['rule_name'])

    # Usage Logs
    op.create_table(
        'usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id', ondelete='SET NULL')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL')),
        sa.Column('action_type', sa.String(50)),
        sa.Column('quantity', sa.Integer(), default=1),
        sa.Column('cost', sa.DECIMAL(10, 6), default=0.00),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_usage_org', 'usage_logs', ['organization_id'])
    op.create_index('idx_usage_created', 'usage_logs', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_usage_org_date', 'usage_logs', ['organization_id', 'created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_usage_ratelimit', 'usage_logs', ['organization_id', 'action_type', 'created_at'], postgresql_ops={'created_at': 'DESC'})

    # Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE')),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id', ondelete='SET NULL')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.Text()),
        sa.Column('endpoint', sa.String(255)),
        sa.Column('http_method', sa.String(10)),
        sa.Column('action_type', sa.String(50)),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('status_code', sa.Integer()),
        sa.Column('error_message', sa.Text()),
        sa.Column('request_id', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_audit_org', 'audit_logs', ['organization_id', 'created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_audit_key', 'audit_logs', ['api_key_id', 'created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_audit_user', 'audit_logs', ['user_id', 'created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_audit_request_id', 'audit_logs', ['request_id'])

    # Job Queue
    op.create_table(
        'job_queue',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('attempts', sa.Integer(), default=0),
        sa.Column('max_attempts', sa.Integer(), default=3),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('worker_id', sa.String(100)),
    )
    op.create_index('idx_job_status', 'job_queue', ['status', 'priority', 'created_at'])
    op.create_index('idx_job_created', 'job_queue', ['created_at'], postgresql_ops={'created_at': 'DESC'})


def downgrade() -> None:
    op.drop_table('job_queue')
    op.drop_table('audit_logs')
    op.drop_table('usage_logs')
    op.drop_table('autofix_recommendations')
    op.drop_table('evaluation_metrics')
    op.drop_table('evaluations')
    op.drop_table('gate_policies')
    op.drop_table('projects')
    op.drop_table('api_keys')
    op.drop_table('users')
    op.drop_table('organizations')
