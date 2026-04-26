"""
Session management routes for TalentMatch.

Session Token Security (Updated)
---------------------------------
JWT tokens are issued ONLY to authenticated users and stored in httpOnly secure cookies.
This protects against XSS attacks (JavaScript cannot access the token).

REMOVED (was insecure):
  - /session/anon endpoint that handed out tokens to anyone
  - localStorage token storage (accessible to XSS)
  - 24-hour default expiry (too long without rate limiting per user)

Routes
------
  POST /session/create — obtain a JWT session token (requires API key auth)
  GET  /session/validate — check if current session is valid

Token Security
  - Issued only to authenticated users (API key required)
  - Stored in httpOnly secure cookie (JavaScript cannot access)
  - Sent automatically by browser on same-origin requests
  - Short-lived by default (configurable via JWT_EXPIRATION_HOURS)
  - Cannot be stolen by XSS (httpOnly prevents JS access)

Frontend Flow
  1. User provides API key (setup/login)
  2. Frontend: POST /session/create with X-API-Key header
  3. Server: Validates key, creates JWT, sets Set-Cookie header
  4. Browser: Stores cookie (JS cannot access)
  5. Subsequent API calls: Browser automatically includes cookie
  6. If JWT expires: Frontend catches 401, redirects to login

Architectural Decision
  For fully unauthenticated/demo access without API key, consider:
  - Option A: Generate a read-only shared API key (fixed in DB, no auth)
  - Option B: Require at least email signup (no password)
  - Option C: Device fingerprinting + aggressive rate limiting
  NOT: Public endpoint that issues tokens (anyone can bypass auth)
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import create_session_token, require_auth, JWT_EXPIRATION_HOURS, generate_api_key, hash_key
from api.config import limiter
from db.models import User, ApiKey
from db.session import get_db
from fastapi import Request
from datetime import datetime, timezone

router = APIRouter(prefix="/session", tags=["session"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SessionCreatedResponse(BaseModel):
    message: str
    expires_in_hours: int


class SessionValidResponse(BaseModel):
    valid: bool
    user_email: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str


class RegisterResponse(BaseModel):
    api_key: str
    email: str
    name: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/create", response_model=SessionCreatedResponse, status_code=200)
async def create_session(
    response: Response,
    current_user: User = Depends(require_auth),
):
    """
    Create a new JWT session token for authenticated user.
    
    Requires authentication via X-API-Key header or existing Bearer token.
    Token is returned in httpOnly secure cookie (not in response body).
    
    Cookie Details:
    - httpOnly: JavaScript cannot access the token
    - secure: Only sent over HTTPS in production
    - samesite=strict: Only sent on same-origin requests (CSRF protection)
    - path=/api/v1: Only sent to API endpoints
    
    Frontend usage:
      1. Call this endpoint with X-API-Key header
      2. Token is automatically stored in httpOnly cookie by browser
      3. All subsequent requests to /api/v1/* automatically include the token
      4. When token expires (401), re-authenticate with API key
    """
    token = create_session_token(current_user.id)
    
    # Set httpOnly cookie — browser will automatically include it in requests
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=JWT_EXPIRATION_HOURS * 3600,  # seconds
        httponly=True,
        secure=True,  # HTTPS only in production
        samesite="strict",  # CSRF protection
        path="/api/v1",
    )
    
    return SessionCreatedResponse(
        message="Session token created. Token stored in httpOnly cookie.",
        expires_in_hours=JWT_EXPIRATION_HOURS,
    )


@router.get("/validate", response_model=SessionValidResponse, status_code=200)
async def validate_session(current_user: User = Depends(require_auth)):
    """
    Validate the current authentication (API key or JWT token).
    Returns 200 if valid, 401 if invalid/expired.
    
    The token (if stored in cookie) is automatically extracted by require_auth.
    """
    return SessionValidResponse(
        valid=True,
        user_email=current_user.email if current_user.email != "anonymous@device.local" else None,
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Public user registration endpoint.
    
    Creates a new user account with the provided email and name.
    Returns a new API key that can be used to log in.
    
    Rate limited to 5 registrations per minute to prevent abuse.
    
    Endpoint: POST /session/register
    """
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == body.email).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A user with that email already exists.")
    
    # Create new user
    user = User(
        email=body.email,
        name=body.name or body.email,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()  # Get the user ID without committing
    
    # Generate API key for new user
    api_key = generate_api_key()
    hashed_key = hash_key(api_key)
    
    api_key_obj = ApiKey(
        user_id=user.id,
        key_hash=hashed_key,
        prefix=api_key[:8],  # First 8 chars for display
        name="Default",
        created_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(api_key_obj)
    
    await db.commit()
    
    return RegisterResponse(
        api_key=api_key,
        email=user.email,
        name=user.name,
    )

