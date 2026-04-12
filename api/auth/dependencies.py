"""
API key authentication for TalentMatch.

Design
------
- Keys are generated as  tm_<32 random hex chars>  (40 chars total)
- Only a SHA-256 hash is stored in the database — the raw key is shown once
  at creation and never again (same model as GitHub PATs)
- FastAPI dependency `require_auth` reads the key from the
  X-API-Key header and validates it against the db on every request
- Key lookup is O(1) via the hash index

Usage
-----
  from api.auth.dependencies import require_auth
  @router.post("/scan/pdf")
  async def scan(current_user: User = Depends(require_auth), ...):
"""

import hashlib
import os
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ApiKey, User
from db.session import get_db

# ---------------------------------------------------------------------------
# Key format & hashing
# ---------------------------------------------------------------------------

KEY_PREFIX = "tm_"
KEY_BYTES  = 32   # 64 hex chars after prefix → 40 chars total key


def generate_api_key() -> str:
    """Return a new raw API key. Show to user once; never store raw."""
    return KEY_PREFIX + secrets.token_hex(KEY_BYTES)


def hash_key(raw_key: str) -> str:
    """SHA-256 hex digest of the raw key — this is what gets stored."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# FastAPI security scheme
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_auth(
    raw_key: str | None = Security(_api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that validates X-API-Key and returns the owning User.
    Raises 401 on missing/invalid key, 403 on inactive user.
    """
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Pass it in the X-API-Key header.",
        )

    key_hash = hash_key(raw_key)

    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)  # noqa: E712
        .limit(1)
    )
    api_key: ApiKey | None = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    # Update last_used timestamp (best-effort — don't fail the request if this errors)
    try:
        await db.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key.id)
            .values(last_used=datetime.now(timezone.utc))
        )
    except Exception:
        pass

    # Load the owning user
    user_result = await db.execute(
        select(User).where(User.id == api_key.user_id).limit(1)
    )
    user: User | None = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return user
