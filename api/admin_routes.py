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
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import generate_api_key, hash_key
from api.config import FREE_SCAN_LIMIT, limiter
from db.models import ApiKey, Candidate, Scan, User
from db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Guard: ADMIN_SECRET header
# ---------------------------------------------------------------------------

def _require_admin(x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")):
    admin_secret = os.getenv("ADMIN_SECRET", "")
    if not admin_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are disabled (ADMIN_SECRET not set).",
        )
    if x_admin_secret != admin_secret:
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


class PaginatedUserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    limit: int
    offset: int


class AdminMetricSnapshot(BaseModel):
    total_users: int
    active_users: int
    users_with_scans: int
    total_scans: int
    total_candidates: int
    active_api_keys: int
    scans_today: int
    candidates_today: int
    avg_score: float
    avg_processing_ms: float
    free_limit_reached: int
    high_confidence_candidates: int


class AdminTrendPoint(BaseModel):
    date: str
    scans: int
    candidates: int


class AdminScoreBucket(BaseModel):
    label: str
    count: int


class AdminRecommendationBreakdown(BaseModel):
    recommendation: str
    count: int


class AdminRoleStat(BaseModel):
    role_title: str
    scans: int
    candidates: int
    avg_score: float


class AdminRecentScan(BaseModel):
    scan_id: str
    created_at: datetime
    user_email: str
    role_title: str
    total_candidates: int
    top_score: float
    avg_score: float
    processing_time_ms: float


class AdminUsageItem(BaseModel):
    user_id: str
    email: str
    scans_used: int
    free_scan_limit: int
    remaining: int
    created_at: datetime


class AdminAnalyticsResponse(BaseModel):
    generated_at: datetime
    free_scan_limit: int
    metrics: AdminMetricSnapshot
    trend: list[AdminTrendPoint]
    score_buckets: list[AdminScoreBucket]
    recommendation_breakdown: list[AdminRecommendationBreakdown]
    top_roles: list[AdminRoleStat]
    recent_scans: list[AdminRecentScan]
    usage: list[AdminUsageItem]


def _as_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _date_key(dt: datetime | None) -> str:
    return _as_utc(dt).date().isoformat()


def _avg(values: list[float]) -> float:
    values = [float(v) for v in values if v is not None]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _score_bucket(score: float) -> str:
    if score >= 85:
        return "85-100"
    if score >= 70:
        return "70-84"
    if score >= 55:
        return "55-69"
    if score >= 40:
        return "40-54"
    return "0-39"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/analytics", response_model=AdminAnalyticsResponse,
            dependencies=[Depends(_require_admin)])
@limiter.limit("10/minute")
async def get_admin_analytics(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Developer dashboard data: product usage, scan quality, and recent activity.
    Kept behind ADMIN_SECRET because it exposes account-level analytics.
    """
    generated_at = datetime.now(timezone.utc)
    today_key = generated_at.date().isoformat()

    users = (await db.execute(select(User))).scalars().all()
    keys = (await db.execute(select(ApiKey))).scalars().all()
    scans = (await db.execute(select(Scan))).scalars().all()
    candidates = (await db.execute(select(Candidate))).scalars().all()

    user_email_by_id = {u.id: u.email for u in users}
    scan_by_id = {s.id: s for s in scans}
    scan_ids_by_user = defaultdict(set)
    candidates_by_scan = defaultdict(list)

    for scan in scans:
        scan_ids_by_user[scan.user_id].add(scan.id)
    for candidate in candidates:
        candidates_by_scan[candidate.scan_id].append(candidate)

    day_start = generated_at.date() - timedelta(days=13)
    trend_map = {
        (day_start + timedelta(days=i)).isoformat(): {"scans": 0, "candidates": 0}
        for i in range(14)
    }
    for scan in scans:
        key = _date_key(scan.created_at)
        if key in trend_map:
            trend_map[key]["scans"] += 1
            trend_map[key]["candidates"] += int(scan.total_candidates or 0)

    bucket_counts = Counter(_score_bucket(float(c.final_score or 0)) for c in candidates)
    bucket_order = ["85-100", "70-84", "55-69", "40-54", "0-39"]
    recommendation_counts = Counter(
        (c.hiring_recommendation or "Unlabeled").strip() or "Unlabeled"
        for c in candidates
    )

    role_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"scans": 0, "candidates": 0, "score_total": 0.0})
    for scan in scans:
        role = (scan.role_title or "Unnamed Scan").strip() or "Unnamed Scan"
        role_stats[role]["scans"] += 1
        role_stats[role]["candidates"] += int(scan.total_candidates or 0)
        role_stats[role]["score_total"] += float(scan.avg_score or 0)

    recent_scans = []
    for scan in sorted(scans, key=lambda s: _as_utc(s.created_at), reverse=True)[:10]:
        recent_scans.append(AdminRecentScan(
            scan_id=scan.id,
            created_at=scan.created_at,
            user_email=user_email_by_id.get(scan.user_id, "Unknown user"),
            role_title=scan.role_title,
            total_candidates=int(scan.total_candidates or 0),
            top_score=round(float(scan.top_score or 0), 1),
            avg_score=round(float(scan.avg_score or 0), 1),
            processing_time_ms=round(float(scan.processing_time_ms or 0), 1),
        ))

    usage = [
        AdminUsageItem(
            user_id=u.id,
            email=u.email,
            scans_used=int(u.free_scans_used or 0),
            free_scan_limit=FREE_SCAN_LIMIT,
            remaining=max(FREE_SCAN_LIMIT - int(u.free_scans_used or 0), 0),
            created_at=u.created_at,
        )
        for u in sorted(users, key=lambda user: int(user.free_scans_used or 0), reverse=True)
    ]

    metrics = AdminMetricSnapshot(
        total_users=len(users),
        active_users=sum(1 for u in users if u.is_active),
        users_with_scans=sum(1 for u in users if scan_ids_by_user.get(u.id)),
        total_scans=len(scans),
        total_candidates=len(candidates),
        active_api_keys=sum(1 for k in keys if k.is_active),
        scans_today=sum(1 for s in scans if _date_key(s.created_at) == today_key),
        candidates_today=sum(
            len(candidates_by_scan[s.id])
            for s in scans
            if _date_key(s.created_at) == today_key
        ),
        avg_score=_avg([c.final_score for c in candidates]),
        avg_processing_ms=_avg([s.processing_time_ms for s in scans]),
        free_limit_reached=sum(1 for u in users if int(u.free_scans_used or 0) >= FREE_SCAN_LIMIT),
        high_confidence_candidates=sum(
            1 for c in candidates if (c.confidence_level or "").lower() == "high"
        ),
    )

    return AdminAnalyticsResponse(
        generated_at=generated_at,
        free_scan_limit=FREE_SCAN_LIMIT,
        metrics=metrics,
        trend=[
            AdminTrendPoint(date=date, scans=values["scans"], candidates=values["candidates"])
            for date, values in trend_map.items()
        ],
        score_buckets=[
            AdminScoreBucket(label=label, count=bucket_counts.get(label, 0))
            for label in bucket_order
        ],
        recommendation_breakdown=[
            AdminRecommendationBreakdown(recommendation=label, count=count)
            for label, count in recommendation_counts.most_common()
        ],
        top_roles=[
            AdminRoleStat(
                role_title=role,
                scans=int(values["scans"]),
                candidates=int(values["candidates"]),
                avg_score=round(values["score_total"] / values["scans"], 1) if values["scans"] else 0.0,
            )
            for role, values in sorted(
                role_stats.items(),
                key=lambda item: (item[1]["scans"], item[1]["candidates"]),
                reverse=True,
            )[:8]
        ],
        recent_scans=recent_scans,
        usage=usage[:25],
    )


@router.post("/users", response_model=CreateUserResponse, status_code=201,
             dependencies=[Depends(_require_admin)])
@limiter.limit("5/minute")
async def create_user(request: Request, body: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A user with that email already exists.")

    user = User(email=body.email)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return CreateUserResponse(id=user.id, email=user.email, created_at=user.created_at)


@router.post("/users/{user_id}/keys", response_model=IssueKeyResponse, status_code=201,
             dependencies=[Depends(_require_admin)])
@limiter.limit("5/minute")
async def issue_key(request: Request, user_id: str, body: IssueKeyRequest, db: AsyncSession = Depends(get_db)):
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
    await db.commit()

    return IssueKeyResponse(key=raw, prefix=api_key.prefix, name=api_key.name)


@router.delete("/keys/{key_id}", status_code=204,
               dependencies=[Depends(_require_admin)])
@limiter.limit("5/minute")
async def revoke_key(request: Request, key_id: str, db: AsyncSession = Depends(get_db)):
    key = await db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found.")
    key.is_active = False
    await db.flush()
    await db.commit()


@router.get("/users", response_model=PaginatedUserListResponse,
            dependencies=[Depends(_require_admin)])
@limiter.limit("5/minute")
async def list_users(request: Request, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    """
    List all users with pagination.
    
    Query parameters:
      - limit: Number of users to return (default 50, max 100)
      - offset: Number of users to skip (default 0)
    """
    # Validate pagination parameters
    limit = min(max(1, limit), 100)  # Clamp between 1 and 100
    offset = max(0, offset)
    
    # Get total count for pagination info
    count_result = await db.execute(select(User))
    total_count = len(count_result.scalars().all())
    
    # Fetch paginated users
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
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
    
    return PaginatedUserListResponse(items=out, total=total_count, limit=limit, offset=offset)
