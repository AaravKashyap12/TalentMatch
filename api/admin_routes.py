"""
Admin routes for TalentMatch.

These endpoints are protected by a separate ADMIN_SECRET env var (simple
shared secret) so they can be called from a setup script or CI without
requiring an existing API key.

Routes
------
  POST /admin/users          — create a new user
  POST /admin/users/{id}/keys — issue an API key for a user
  DELETE /admin/keys/{id}    — revoke a key
  GET  /admin/users          — list all users (with key prefixes)
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import generate_api_key, hash_key
from db.models import ApiKey, User
from db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Guard: ADMIN_SECRET header
# ---------------------------------------------------------------------------

_ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def _require_admin(x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")):
    if not _ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are disabled (ADMIN_SECRET not set).",
        )
    if x_admin_secret != _ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret.",
        )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    email: EmailStr


class CreateUserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime


class IssueKeyRequest(BaseModel):
    name: str | None = None


class IssueKeyResponse(BaseModel):
    key: str           # shown ONCE — store it now
    prefix: str
    name: str | None


class UserListItem(BaseModel):
    id: str
    email: str
    is_active: bool
    created_at: datetime
    key_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/users", response_model=CreateUserResponse, status_code=201,
             dependencies=[Depends(_require_admin)])
async def create_user(body: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A user with that email already exists.")

    user = User(email=body.email)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return CreateUserResponse(id=user.id, email=user.email, created_at=user.created_at)


@router.post("/users/{user_id}/keys", response_model=IssueKeyResponse, status_code=201,
             dependencies=[Depends(_require_admin)])
async def issue_key(user_id: str, body: IssueKeyRequest, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive.")

    raw = generate_api_key()
    api_key = ApiKey(
        user_id=user_id,
        key_hash=hash_key(raw),
        prefix=raw[:8],
        name=body.name,
    )
    db.add(api_key)
    await db.flush()

    return IssueKeyResponse(key=raw, prefix=api_key.prefix, name=api_key.name)


@router.delete("/keys/{key_id}", status_code=204,
               dependencies=[Depends(_require_admin)])
async def revoke_key(key_id: str, db: AsyncSession = Depends(get_db)):
    key = await db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found.")
    key.is_active = False
    await db.flush()


@router.get("/users", response_model=list[UserListItem],
            dependencies=[Depends(_require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    out = []
    for u in users:
        keys_result = await db.execute(
            select(ApiKey).where(ApiKey.user_id == u.id, ApiKey.is_active == True)  # noqa: E712
        )
        out.append(UserListItem(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            created_at=u.created_at,
            key_count=len(keys_result.scalars().all()),
        ))
    return out
