"""In-memory rate limiting via FastAPI dependencies.

Two buckets:
  _general_buckets  — 100 req/min per user (all authenticated endpoints)
  _evaluate_buckets — 20 evals/hour per user (POST /v1/evaluate only)

Dev-mode bypass mirrors auth.py._is_dev_mode().
"""
import time
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse

from evalkit.auth import get_current_user_id
from evalkit.config import settings

_general_buckets: dict[str, list[float]] = {}
_evaluate_buckets: dict[str, list[float]] = {}
_call_counter = 0


def _is_dev_mode() -> bool:
    if settings.environment in ("production", "prod"):
        return False
    return (
        settings.environment in ("development", "dev", "test")
        and not settings.clerk_secret_key
    )


def check_rate_limit(
    user_id: str,
    max_requests: int,
    window_seconds: int,
    buckets: dict[str, list[float]],
) -> None:
    global _call_counter
    now = time.monotonic()
    cutoff = now - window_seconds
    timestamps = buckets.get(user_id, [])
    timestamps = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= max_requests:
        oldest = timestamps[0]
        retry_after = int(oldest + window_seconds - now) + 1
        retry_after = max(retry_after, 1)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    timestamps.append(now)
    buckets[user_id] = timestamps

    _call_counter += 1
    if _call_counter % 100 == 0:
        _cleanup_stale(buckets, window_seconds)


def _cleanup_stale(buckets: dict[str, list[float]], window_seconds: int) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds
    stale = [uid for uid, ts in buckets.items() if not ts or ts[-1] <= cutoff]
    for uid in stale:
        del buckets[uid]


def reset_state() -> None:
    _general_buckets.clear()
    _evaluate_buckets.clear()
    global _call_counter
    _call_counter = 0


async def enforce_rate_limit(
    user_id: str = Depends(get_current_user_id),
) -> str:
    if _is_dev_mode():
        return user_id
    check_rate_limit(
        user_id,
        settings.rate_limit_requests_per_minute,
        60,
        _general_buckets,
    )
    return user_id


async def enforce_rate_limit_evaluate(
    user_id: str = Depends(get_current_user_id),
) -> str:
    if _is_dev_mode():
        return user_id
    check_rate_limit(
        user_id,
        settings.rate_limit_requests_per_minute,
        60,
        _general_buckets,
    )
    check_rate_limit(
        user_id,
        settings.rate_limit_evaluate_per_hour,
        3600,
        _evaluate_buckets,
    )
    return user_id
