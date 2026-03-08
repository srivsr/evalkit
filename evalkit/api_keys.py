"""API key management router for EvalKit v2."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from evalkit.auth import get_current_user_id
from evalkit.rate_limit import enforce_rate_limit
from evalkit.storage import sqlite as storage

router = APIRouter(prefix="/v1/api-keys", tags=["api-keys"])


class CreateKeyRequest(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None


class CreateKeyResponse(ApiKeyResponse):
    key: str


@router.post("", response_model=CreateKeyResponse, status_code=201)
async def create_api_key(req: CreateKeyRequest, user_id: str = Depends(enforce_rate_limit)):
    from evalkit.main import get_db
    db = get_db()
    result = await storage.create_api_key(db, user_id, req.name)
    return CreateKeyResponse(**result)


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(user_id: str = Depends(enforce_rate_limit)):
    from evalkit.main import get_db
    db = get_db()
    return await storage.list_api_keys(db, user_id)


@router.delete("/{key_id}", status_code=200)
async def revoke_api_key(key_id: str, user_id: str = Depends(enforce_rate_limit)):
    from evalkit.main import get_db
    db = get_db()
    success = await storage.revoke_api_key(db, key_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found or already revoked")
    return {"id": key_id, "revoked": True}
