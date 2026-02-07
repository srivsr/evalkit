from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from ..database import get_db
from ..config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health():
    return {"status": "healthy"}


@router.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    checks = {
        "database": False,
        "redis": False,
        "llm_keys": False,
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        checks["redis"] = True
    except Exception:
        pass

    # Check LLM keys configured
    checks["llm_keys"] = bool(settings.anthropic_api_key or settings.openai_api_key)

    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
    }
