"""Subscription tiers and quota enforcement for EvalKit v2.

Tiers:
  free  - 50 evals/month, 3 projects, limited judge models
  basic - 500 evals/month, 10 projects, GPT-4o + Claude Sonnet
  pro   - 5000 evals/month, unlimited projects, all models
"""
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

TIER_CONFIGS: dict[str, dict] = {
    "free": {
        "evaluations_per_month": 50,
        "max_projects": 3,
        "judge_models": ["gpt-4o-mini"],
        "price_usd": 0,
        "label": "Free",
    },
    "basic": {
        "evaluations_per_month": 500,
        "max_projects": 10,
        "judge_models": ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-20250514"],
        "price_usd": 19,
        "label": "Basic",
    },
    "pro": {
        "evaluations_per_month": 5000,
        "max_projects": 9999,
        "judge_models": ["all"],
        "price_usd": 49,
        "label": "Pro",
    },
}

PAID_TIERS = {k: v for k, v in TIER_CONFIGS.items() if v["price_usd"] > 0}


def get_tier_config(tier: str) -> dict:
    if tier not in TIER_CONFIGS:
        raise ValueError(f"Unknown tier: {tier}. Valid tiers: {list(TIER_CONFIGS.keys())}")
    return TIER_CONFIGS[tier]


async def check_quota(user_id: str, db) -> dict:
    cursor = await db.execute("SELECT tier FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    tier = dict(row)["tier"] if row else "free"
    config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])

    cursor = await db.execute(
        """SELECT COUNT(*) as cnt FROM evaluations e
           JOIN projects p ON e.project_id = p.id
           WHERE p.user_id = ?
           AND e.created_at >= datetime('now', 'start of month')""",
        (user_id,),
    )
    row = await cursor.fetchone()
    used = dict(row)["cnt"] if row else 0

    limit = config["evaluations_per_month"]
    return {
        "tier": tier,
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }


async def enforce_quota(user_id: str, db) -> None:
    quota = await check_quota(user_id, db)
    if quota["remaining"] <= 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": f"Monthly evaluation limit reached ({quota['limit']}). Upgrade your plan.",
                "tier": quota["tier"],
                "used": quota["used"],
                "limit": quota["limit"],
            },
        )


async def check_project_limit(user_id: str, db) -> None:
    cursor = await db.execute("SELECT tier FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    tier = dict(row)["tier"] if row else "free"
    config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])

    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM projects WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    count = dict(row)["cnt"] if row else 0

    if count >= config["max_projects"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "project_limit_reached",
                "message": f"Project limit reached ({config['max_projects']}). Upgrade your plan.",
                "tier": tier,
                "count": count,
                "limit": config["max_projects"],
            },
        )
