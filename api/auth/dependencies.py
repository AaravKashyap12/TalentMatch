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

Session Tokens
--------------
- Frontend can also authenticate using JWT session tokens via Authorization header
- Tokens are issued by POST /session endpoint (anonymous or API-key protected)
- Tokens expire after JWT_EXPIRATION_HOURS (prevents long-lived secrets in bundle)
- This allows frontend to avoid embedding permanent API keys

Usage
-----
  from api.auth.dependencies import require_auth
  @router.post("/scan/pdf")
  async def scan(current_user: User = Depends(require_auth), ...):
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ApiKey, User
from db.session import get_db

# ---------------------------------------------------------------------------
# JWT Configuration
# ---------------------------------------------------------------------------

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

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
# FastAPI security schemes
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)# ---------------------------------------------------------------------------
# JWT Session Tokens (for frontend use)
# ---------------------------------------------------------------------------

def create_session_token(user_id: str) -> str:
    """
    Create a short-lived JWT token for frontend use.
    Avoids embedding permanent API keys in client bundles.
    """
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "exp": expiration,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_session_token(token: str) -> str:
    """
    Verify and decode JWT token. Returns user_id on success.
    Raises HTTPException on invalid/expired token.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id.",
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token expired. Request a new one from /session/create.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
        )


def verify_supabase_claims(token: str) -> dict:
    """
    Verify Supabase JWT token. Returns decoded claims on success.
    Raises HTTPException on invalid/expired token.
    
    Supabase tokens contain the user's UUID in the 'sub' claim.
    """
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    if token == "mock-token" and dev_mode:
        return {"sub": "dev-id", "email": "dev@local"}

    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT secret not configured",
        )
    
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase token: missing user_id.",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase token expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Supabase token.",
        )


def verify_supabase_token(token: str) -> str:
    """Verify a Supabase JWT token and return its user id."""
    return verify_supabase_claims(token)["sub"]


_bearer_scheme = HTTPBearer(auto_error=False)


async def _get_active_user(db: AsyncSession, user_id: str) -> User:
    user_result = await db.execute(
        select(User).where(User.id == user_id).limit(1)
    )
    user: User | None = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    return user


async def _get_or_create_supabase_user(db: AsyncSession, claims: dict) -> User:
    user_id = claims["sub"]
    user_result = await db.execute(
        select(User).where(User.id == user_id).limit(1)
    )
    user: User | None = user_result.scalar_one_or_none()

    if user is None:
        email = claims.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase token: missing email.",
            )
        metadata = claims.get("user_metadata") or {}
        user = User(
            id=user_id,
            email=email,
            name=metadata.get("name") or metadata.get("full_name"),
            is_active=True,
        )
        db.add(user)
        await db.flush()
        return user

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    return user


async def require_auth(
    session_token: str | None = Cookie(None),
    api_key: str | None = Security(_api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that validates authentication from multiple sources:
      1. session_token cookie (httpOnly, set by /session/create)
      2. Authorization: Bearer <token> header (Supabase JWT or session JWT)
      3. X-API-Key header (API key)
    
    Returns the authenticated User. Raises 401 on missing/invalid credentials.
    
    Priority order:
      1. Cookie (most secure - httpOnly)
      2. Bearer token (Authorization header - tries Supabase first, then session token)
      3. API Key (X-API-Key header)
    """
    # Try session cookie first (httpOnly, most secure)
    if session_token:
        try:
            user_id = verify_session_token(session_token)
            return await _get_active_user(db, user_id)
        except HTTPException:
            # Token invalid/expired, fall through to try other methods
            pass

    # Try Authorization: Bearer header (Supabase or session token)
    if bearer:
        # Try Supabase token first (if configured)
        if SUPABASE_JWT_SECRET:
            try:
                claims = verify_supabase_claims(bearer.credentials)
                return await _get_or_create_supabase_user(db, claims)
            except HTTPException:
                # Try session token as fallback
                pass
        
        # Try session token as fallback
        try:
            user_id = verify_session_token(bearer.credentials)
            return await _get_active_user(db, user_id)
        except HTTPException:
            # Bearer token invalid, fall through to API key
            pass

    # Fall back to API key auth
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials. Pass API key in X-API-Key header, Bearer token in Authorization header, or obtain a session cookie via /session/create.",
        )

    key_hash = hash_key(api_key)

    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)  # noqa: E712
        .limit(1)
    )
    api_key_obj: ApiKey | None = result.scalar_one_or_none()

    if api_key_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    # Update last_used timestamp (best-effort — don't fail the request if this errors)
    try:
        await db.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key_obj.id)
            .values(last_used=datetime.now(timezone.utc))
        )
    except Exception:
        pass

    # Load the owning user
    user_result = await db.execute(
        select(User).where(User.id == api_key_obj.user_id).limit(1)
    )
    user: User | None = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return user
