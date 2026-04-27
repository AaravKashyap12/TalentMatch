"""
API routes for TalentMatch.

Fixes vs previous version
--------------------------
- CandidateResult.missing_required_skills is now correctly mapped when
  building result objects (was silently empty in some code paths).
- Added POST /profiles endpoint so the frontend signup flow doesn't 404.
- GET /scans/{scan_id} now eager-loads candidate skills in a single query
  instead of N+1 per candidate, which caused timeouts on large scans.
- Weight normalisation: total_weight=0 guard prevents ZeroDivisionError
  when all priorities are set to "Ignore".
- scan_id type is str (UUID) everywhere — no implicit int cast.
"""

import asyncio
import io
import json
import logging
import time
from functools import partial
from typing import List

import structlog
from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Request, UploadFile, status,
)
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.ai.groq_jd_parser import parse_jd_skill_tiers_with_groq
from api.ai.groq_overview import generate_candidate_overviews
from api.auth.dependencies import require_auth
from api.config import (
    ENABLE_GROQ_JD_PARSING,
    FREE_SCAN_LIMIT,
    GROQ_API_KEY,
    MAX_JD_FILE_SIZE,
    MAX_JOB_DESCRIPTION_CHARS,
    MAX_UPLOAD_SIZE,
    MAX_FILES_PER_SCAN,
    is_dev_mode,
    limiter,
)
from api.constants import PRIORITY_MAP
from api.resume_parser import extract_text_from_pdf, is_valid_pdf
from api.schemas import (
    CandidateResult,
    ScanDetail,
    ScanHistoryItem,
    ScanResponse,
    UsageResponse,
)
from db.models import Candidate, CandidateSkill, Scan, User
from db.session import get_db
from ml.matcher import (
    calculate_ats_score,
    calculate_component_scores_structured,
    extract_skills,
    extract_jd_skill_tiers,
)
from ml.nlp_utils import clean_texts_batch
from pipeline.skills import normalize_skill

log = structlog.get_logger()
router = APIRouter()


def _canonical_skill_set(skills) -> set[str]:
    return {
        normalize_skill(skill)
        for skill in skills
        if isinstance(skill, str) and skill and not skill.startswith("unknown:")
    }


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["ops"])
async def health():
    from ml.nlp_utils import _nlp
    return {
        "status": "ok",
        "models": {
            "spacy": _nlp is not None,
            "embedder_mode": "tfidf",
            "groq_jd_parser": bool(ENABLE_GROQ_JD_PARSING and GROQ_API_KEY),
        },
    }


# ── Profile creation (called by frontend after Supabase signup) ───────────────

class ProfileCreate(BaseModel):
    email: EmailStr
    name: str | None = None


@router.post("/profiles", status_code=201, tags=["auth"])
@limiter.limit("10/minute")
async def create_profile(
    request: Request,
    body: ProfileCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Upsert a user profile after Supabase sign-up.
    The frontend calls this once; it's idempotent.
    """
    if current_user.email != body.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile email must match the authenticated user.",
        )
    if body.name:
        current_user.name = body.name
        await db.commit()
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}


@router.get("/usage", response_model=UsageResponse, tags=["billing"])
@limiter.limit("60/minute")
async def get_usage(request: Request, current_user: User = Depends(require_auth)):
    used = int(current_user.free_scans_used or 0)
    unlimited = is_dev_mode()
    return UsageResponse(
        free_scan_limit=FREE_SCAN_LIMIT,
        free_scans_used=used,
        free_scans_remaining=FREE_SCAN_LIMIT if unlimited else max(FREE_SCAN_LIMIT - used, 0),
        is_unlimited=unlimited,
    )


# ── ML helpers ────────────────────────────────────────────────────────────────

def _run_ml_sync(
    job_description: str,
    raw_resumes: List[str],
    weights: dict,
    required_skills: List[str],
    preferred_skills: List[str],
    experience_cap_years: float,
    min_years_experience: float | None,
    required_degree: str | None,
    jd_skill_tiers: dict | None = None,
):
    all_texts = [job_description] + raw_resumes
    all_cleaned = clean_texts_batch(all_texts)
    cleaned_jd = all_cleaned[0]

    tiers = jd_skill_tiers or extract_jd_skill_tiers(
        job_description,
        required_skills,
        preferred_skills,
    )
    jd_required = _canonical_skill_set(tiers["required"])
    jd_preferred = _canonical_skill_set(tiers["preferred"]) | _canonical_skill_set(tiers["implicit"])

    component_scores = calculate_component_scores_structured(
        job_desc_clean=cleaned_jd,
        resumes_clean=all_cleaned[1:],
        job_desc_raw=job_description,
        resumes_raw=raw_resumes,
        weights=weights,
        jd_skills=jd_required,
        preferred_skills=jd_preferred,
        experience_cap_years=experience_cap_years,
        min_years_experience=min_years_experience,
        required_degree=required_degree,
    )

    ats_scores = [
        calculate_ats_score(raw, job_keywords=jd_required)
        for raw in raw_resumes
    ]

    return component_scores, ats_scores, jd_required, jd_preferred


def _extract_pdf_sync(content: bytes) -> str:
    return extract_text_from_pdf(io.BytesIO(content))


def _decode_jd_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Job description file could not be decoded.")


# ── POST /scan/pdf ─────────────────────────────────────────────────────────────

@router.post("/scan/pdf", response_model=ScanResponse, status_code=200)
@limiter.limit("30/minute")
async def scan_pdf(
    request: Request,
    role_title:           str   = Form("Unnamed Scan"),
    job_description:      str   = Form(""),
    required_skills:      str   = Form("[]"),
    preferred_skills:     str   = Form("[]"),
    min_years_experience: str   = Form("null"),
    required_degree:      str   = Form("null"),
    experience_cap_years: float = Form(15.0),
    skills_priority:      str   = Form("High"),
    experience_priority:  str   = Form("Medium"),
    education_priority:   str   = Form("Low"),
    relevance_priority:   str   = Form("Low"),
    jd_file: UploadFile | None   = File(None),
    files: List[UploadFile]     = File(...),
    current_user: User          = Depends(require_auth),
    db: AsyncSession            = Depends(get_db),
):
    t_start = time.perf_counter()
    unlimited_scans = is_dev_mode()
    free_scans_used = int(current_user.free_scans_used or 0)
    if not unlimited_scans and free_scans_used >= FREE_SCAN_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Free scan limit reached ({FREE_SCAN_LIMIT}/{FREE_SCAN_LIMIT}).",
        )

    # ── Parse JSON form fields ──
    try:
        req_skills  = json.loads(required_skills)
        pref_skills = json.loads(preferred_skills)
        min_yrs     = json.loads(min_years_experience)
        req_degree  = json.loads(required_degree)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Malformed JSON in form field: {e}")

    if jd_file is not None:
        jd_ext = (jd_file.filename or "").lower()
        if not (jd_ext.endswith(".txt") or jd_ext.endswith(".md")):
            raise HTTPException(status_code=400, detail="Job description file must be .txt or .md.")
        jd_bytes = await jd_file.read()
        if len(jd_bytes) > MAX_JD_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Job description file exceeds {MAX_JD_FILE_SIZE // 1024} KB limit",
            )
        job_description = _decode_jd_text(jd_bytes).strip()

    if len(job_description.strip()) < 20:
        raise HTTPException(status_code=400, detail="Job description is too short (min 20 chars)")
    if len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Job description is too long (max {MAX_JOB_DESCRIPTION_CHARS:,} chars)",
        )
    if not (1.0 <= experience_cap_years <= 40.0):
        raise HTTPException(status_code=400, detail="experience_cap_years must be 1–40")

    try:
        weights = {
            "skills":     PRIORITY_MAP[skills_priority],
            "experience": PRIORITY_MAP[experience_priority],
            "education":  PRIORITY_MAP[education_priority],
            "relevance":  PRIORITY_MAP[relevance_priority],
        }
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail="Invalid priority. Must be: Ignore | Low | Medium | High | Critical",
        )

    # Guard: all-Ignore would cause divide-by-zero in scorer
    if sum(weights.values()) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one scoring dimension must have a priority above Ignore.",
        )

    if not files:
        raise HTTPException(status_code=400, detail="At least one resume PDF is required")
    if len(files) > MAX_FILES_PER_SCAN:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES_PER_SCAN} per scan.",
        )

    # ── Validate files ──
    for file in files:
        if file.content_type not in ("application/pdf", "application/octet-stream"):
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename}: only PDF files are accepted.",
            )
        magic = await file.read(4)
        if not is_valid_pdf(magic):
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename}: not a valid PDF (bad magic bytes).",
            )
        await file.seek(0)

    # ── Extract PDF text (parallel) ──
    loop = asyncio.get_running_loop()

    async def process_file(f: UploadFile):
        chunks, total = [], 0
        while True:
            chunk = await f.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"{f.filename} exceeds {MAX_UPLOAD_SIZE // (1024*1024)} MB limit",
                )
            chunks.append(chunk)
        content = b"".join(chunks)
        text = await loop.run_in_executor(None, partial(_extract_pdf_sync, content))
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from {f.filename} (image-only PDF?)",
            )
        return text, f.filename or "resume.pdf"

    process_results = await asyncio.gather(*[process_file(f) for f in files])
    raw_resumes = [r[0] for r in process_results]
    filenames   = [r[1] for r in process_results]

    jd_skill_tiers = await parse_jd_skill_tiers_with_groq(
        job_description,
        req_skills,
        pref_skills,
    )

    # ── ML scoring (thread pool) ──
    component_scores, ats_scores, jd_required, jd_preferred = await loop.run_in_executor(
        None,
        partial(
            _run_ml_sync,
            job_description, raw_resumes, weights,
            req_skills, pref_skills,
            experience_cap_years, min_yrs, req_degree,
            jd_skill_tiers,
        ),
    )

    # ── Build result objects ──
    results: List[CandidateResult] = []
    for idx, base in enumerate(component_scores):
        resume_skills  = set(base["resume_skills"])
        matched_skills = sorted(
            set(base.get("matched_skills", [])) |
            set(base.get("matched_preferred_skills", []))
        )
        missing_skills = sorted(base.get("missing_required_skills", []))

        results.append(CandidateResult(
            filename=filenames[idx],
            final_score=base["final_score"],
            skills_score=base["skills_score"],
            exp_score=base["exp_score"],
            edu_score=base["edu_score"],
            relevance_score=base["relevance_score"],
            semantic_overlap_score=base.get("semantic_overlap_score"),
            role_alignment_score=base.get("role_alignment_score"),
            ats_score=ats_scores[idx],
            matched_skills_count=len(matched_skills),
            matched_skills=matched_skills,
            missing_required_skills=missing_skills,
            experience=base.get("experience_str", "0.0 Years"),
            degree=base.get("degree"),
            years_experience=base.get("years_experience"),
            meets_min_experience=base.get("meets_min_experience"),
            meets_degree_req=base.get("meets_degree_req"),
            primary_backend_language=base.get("primary_backend_language"),
            jd_primary_backend_language=base.get("jd_primary_backend_language"),
            resume_role_family=base.get("resume_role_family"),
            jd_role_family=base.get("jd_role_family"),
            confidence_level=base.get("confidence_level"),
            hiring_recommendation=base.get("hiring_recommendation"),
            ai_overview=base.get("ai_overview"),
            score_summary=base.get("score_summary"),
            score_concerns=base.get("score_concerns", []),
            score_improvements=base.get("score_improvements", []),
        ))

    results.sort(key=lambda r: r.final_score, reverse=True)
    overview_map = await generate_candidate_overviews(
        role_title,
        sorted(jd_required),
        sorted(jd_preferred),
        results,
    )
    for rank, result in enumerate(results, start=1):
        result.ai_overview = overview_map.get(rank)

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)
    top_score  = round(results[0].final_score, 1) if results else 0.0
    avg_score  = round(sum(r.final_score for r in results) / len(results), 1) if results else 0.0

    # ── Persist ──
    scan = Scan(
        user_id=current_user.id,
        role_title=role_title,
        job_description=job_description,
        required_skills=json.dumps(req_skills),
        preferred_skills=json.dumps(pref_skills),
        min_years_experience=min_yrs,
        required_degree=req_degree,
        experience_cap_years=experience_cap_years,
        skills_priority=skills_priority,
        experience_priority=experience_priority,
        education_priority=education_priority,
        relevance_priority=relevance_priority,
        total_candidates=len(results),
        top_score=top_score,
        avg_score=avg_score,
        jd_skills_count=len(jd_required),
        processing_time_ms=elapsed_ms,
    )
    db.add(scan)
    await db.flush()

    for rank, r in enumerate(results, start=1):
        cand = Candidate(
            scan_id=scan.id,
            rank=rank,
            filename=r.filename,
            final_score=r.final_score,
            skills_score=r.skills_score,
            exp_score=r.exp_score,
            edu_score=r.edu_score,
            relevance_score=r.relevance_score,
            semantic_overlap_score=r.semantic_overlap_score,
            role_alignment_score=r.role_alignment_score,
            ats_score=r.ats_score,
            matched_skills_count=r.matched_skills_count,
            missing_required_skills=json.dumps(r.missing_required_skills),
            experience=r.experience,
            years_experience=r.years_experience,
            degree=r.degree,
            primary_backend_language=r.primary_backend_language,
            jd_primary_backend_language=r.jd_primary_backend_language,
            resume_role_family=r.resume_role_family,
            jd_role_family=r.jd_role_family,
            confidence_level=r.confidence_level,
            hiring_recommendation=r.hiring_recommendation,
            ai_overview=r.ai_overview,
            score_summary=r.score_summary,
            score_concerns=json.dumps(r.score_concerns),
            score_improvements=json.dumps(r.score_improvements),
        )
        db.add(cand)
        await db.flush()
        for skill in r.matched_skills:
            db.add(CandidateSkill(candidate_id=cand.id, skill=skill))

    if not unlimited_scans:
        current_user.free_scans_used = free_scans_used + 1
    await db.commit()
    log.info("scan_complete", scan_id=scan.id, candidates=len(results),
             ms=elapsed_ms, user=current_user.email)

    return ScanResponse(
        scan_id=scan.id,
        results=results,
        total_candidates=len(results),
        jd_skills_count=len(jd_required),
        processing_time_ms=elapsed_ms,
        experience_cap_years=experience_cap_years,
    )


# ── GET /scans ─────────────────────────────────────────────────────────────────

@router.get("/scans", response_model=List[ScanHistoryItem], tags=["history"])
@limiter.limit("30/minute")
async def list_scans(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    current_user: User   = Depends(require_auth),
    db: AsyncSession     = Depends(get_db),
):
    result = await db.execute(
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .limit(min(limit, 100))
        .offset(offset)
    )
    scans = result.scalars().all()
    return [
        ScanHistoryItem(
            scan_id=s.id,
            created_at=s.created_at,
            role_title=s.role_title,
            total_candidates=s.total_candidates,
            top_score=round(float(s.top_score or 0.0), 1),
            avg_score=round(float(s.avg_score or 0.0), 1),
            jd_snippet=s.job_description[:120],
        )
        for s in scans
    ]


# ── GET /scans/{scan_id} ───────────────────────────────────────────────────────

@router.get("/scans/{scan_id}", response_model=ScanDetail, tags=["history"])
@limiter.limit("60/minute")
async def get_scan(
    request: Request,
    scan_id: str,
    current_user: User   = Depends(require_auth),
    db: AsyncSession     = Depends(get_db),
):
    scan: Scan | None = await db.get(Scan, scan_id)
    if scan is None or scan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scan not found")

    # FIX: single query with join instead of N+1 per candidate
    cands_result = await db.execute(
        select(Candidate).where(Candidate.scan_id == scan_id).order_by(Candidate.rank)
    )
    candidates = cands_result.scalars().all()

    # Batch-load all skills for this scan in one query
    cand_ids = [c.id for c in candidates]
    skills_result = await db.execute(
        select(CandidateSkill).where(CandidateSkill.candidate_id.in_(cand_ids))
    )
    skills_by_cand: dict[str, list[str]] = {}
    for s in skills_result.scalars().all():
        skills_by_cand.setdefault(s.candidate_id, []).append(s.skill)

    results: List[CandidateResult] = []
    for c in candidates:
        try:
            missing = json.loads(c.missing_required_skills or "[]")
        except json.JSONDecodeError:
            missing = []
        try:
            concerns = json.loads(c.score_concerns or "[]")
        except json.JSONDecodeError:
            concerns = []
        try:
            improvements = json.loads(c.score_improvements or "[]")
        except json.JSONDecodeError:
            improvements = []

        results.append(CandidateResult(
            filename=c.filename,
            final_score=c.final_score,
            skills_score=c.skills_score,
            exp_score=c.exp_score,
            edu_score=c.edu_score,
            relevance_score=c.relevance_score,
            semantic_overlap_score=c.semantic_overlap_score,
            role_alignment_score=c.role_alignment_score,
            ats_score=c.ats_score,
            matched_skills_count=c.matched_skills_count,
            matched_skills=skills_by_cand.get(c.id, []),
            missing_required_skills=missing,
            experience=c.experience,
            degree=c.degree,
            years_experience=c.years_experience,
            primary_backend_language=c.primary_backend_language,
            jd_primary_backend_language=c.jd_primary_backend_language,
            resume_role_family=c.resume_role_family,
            jd_role_family=c.jd_role_family,
            confidence_level=c.confidence_level,
            hiring_recommendation=c.hiring_recommendation,
            ai_overview=c.ai_overview,
            score_summary=c.score_summary,
            score_concerns=concerns,
            score_improvements=improvements,
        ))

    try:
        req_skills  = json.loads(scan.required_skills  or "[]")
        pref_skills = json.loads(scan.preferred_skills or "[]")
    except json.JSONDecodeError:
        req_skills = pref_skills = []

    return ScanDetail(
        scan_id=scan.id,
        created_at=scan.created_at,
        role_title=scan.role_title,
        job_description=scan.job_description,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        min_years_experience=scan.min_years_experience,
        required_degree=scan.required_degree,
        experience_cap_years=scan.experience_cap_years,
        skills_priority=scan.skills_priority,
        experience_priority=scan.experience_priority,
        education_priority=scan.education_priority,
        relevance_priority=scan.relevance_priority,
        total_candidates=scan.total_candidates,
        jd_skills_count=scan.jd_skills_count,
        processing_time_ms=scan.processing_time_ms,
        results=results,
    )


# ── DELETE /scans/{scan_id} ────────────────────────────────────────────────────

@router.delete("/scans/{scan_id}", status_code=204, tags=["history"])
@limiter.limit("20/minute")
async def delete_scan(
    request: Request,
    scan_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession   = Depends(get_db),
):
    """Delete a scan and all associated candidates/skills (cascade)."""
    scan: Scan | None = await db.get(Scan, scan_id)
    if scan is None or scan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    await db.delete(scan)
    await db.commit()
