import hashlib
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import APIKey


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def authenticate_api_key(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    key = authorization.replace("Bearer ", "")
    key_hash = hash_api_key(key)

    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.revoked == False
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="API key expired")

    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return api_key


def require_scope(scope: str):
    async def check_scope(api_key: APIKey = Depends(authenticate_api_key)) -> APIKey:
        if scope not in api_key.scopes:
            raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")
        return api_key
    return check_scope
