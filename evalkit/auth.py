"""Clerk authentication for EvalKit v2.

Pattern: Local JWT verification using Clerk's JWKS endpoint.
Dev mode: bypasses token verification when EVALKIT_ENVIRONMENT=development
and no EVALKIT_CLERK_SECRET_KEY is set.
"""
import logging
from typing import Optional

import httpx
from jose import jwt, jwk, JWTError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from evalkit.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

DEV_USER_ID = "dev-user-001"
DEV_USER_EMAIL = "dev@evalkit.local"

_http_client: Optional[httpx.AsyncClient] = None
_jwks_cache: dict = {"keys": [], "fetched_at": 0}
JWKS_CACHE_TTL = 3600


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def close_http_client():
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


def _is_dev_mode() -> bool:
    if settings.environment in ("production", "prod"):
        return False
    return (
        settings.environment in ("development", "dev", "test")
        and not settings.clerk_secret_key
    )


def _get_clerk_issuer() -> str:
    """Extract issuer URL from the publishable key."""
    pk = settings.clerk_publishable_key or ""
    if pk.startswith("pk_test_") or pk.startswith("pk_live_"):
        import base64
        try:
            encoded = pk.split("_", 2)[2]
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += "=" * padding
            domain = base64.b64decode(encoded).decode().rstrip("$")
            return f"https://{domain}"
        except Exception:
            pass
    return ""


async def _get_jwks() -> list[dict]:
    """Fetch and cache Clerk's JWKS keys."""
    import time
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < JWKS_CACHE_TTL:
        return _jwks_cache["keys"]

    issuer = _get_clerk_issuer()
    if not issuer:
        return _jwks_cache["keys"]

    jwks_url = f"{issuer}/.well-known/jwks.json"
    client = await get_http_client()
    try:
        resp = await client.get(jwks_url)
        if resp.status_code == 200:
            keys = resp.json().get("keys", [])
            _jwks_cache["keys"] = keys
            _jwks_cache["fetched_at"] = now
            logger.info(f"Fetched {len(keys)} JWKS keys from Clerk")
            return keys
    except Exception as e:
        logger.error(f"JWKS fetch error: {e}")

    return _jwks_cache["keys"]


async def verify_clerk_token(token: str) -> dict[str, str]:
    if not settings.clerk_secret_key:
        if _is_dev_mode():
            logger.warning("Auth dev-mode active — all requests use DEV_USER_ID.")
            return {"user_id": DEV_USER_ID, "email": DEV_USER_EMAIL}
        raise HTTPException(status_code=503, detail="Authentication service not configured")

    issuer = _get_clerk_issuer()
    jwks_keys = await _get_jwks()

    if not jwks_keys:
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        matching_key = None
        for key in jwks_keys:
            if key.get("kid") == kid:
                matching_key = key
                break

        if not matching_key:
            _jwks_cache["fetched_at"] = 0
            jwks_keys = await _get_jwks()
            for key in jwks_keys:
                if key.get("kid") == kid:
                    matching_key = key
                    break

        if not matching_key:
            raise HTTPException(status_code=401, detail="Token signing key not found")

        rsa_key = jwk.construct(matching_key)
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},
        )

        user_id = payload.get("sub")
        email = payload.get("email", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")

        return {"user_id": user_id, "email": email}

    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def _check_api_key(request: Request) -> Optional[str]:
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    from evalkit.storage import sqlite as storage
    from evalkit.main import get_db
    db = get_db()
    user_id = await storage.validate_api_key(db, api_key)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return user_id


async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    api_key_user = await _check_api_key(request)
    if api_key_user:
        return api_key_user
    if not credentials:
        if _is_dev_mode():
            return DEV_USER_ID
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_data = await verify_clerk_token(credentials.credentials)
    return user_data["user_id"]
