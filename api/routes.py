"""
API routes for TalentMatch.

Changes vs original
-------------------
- scan_pdf is now fully async — PDF parsing and ML inference run in a
  thread pool via asyncio.get_event_loop().run_in_executor so the event
  loop is never blocked.
- Requires authentication via X-API-Key header (require_auth dependency).
- Accepts a structured JobDescription JSON body (+ multipart files).
- Persists every scan and its results to the database.
- Adds GET /scans and GET /scans/{id} for history retrieval.
- Adds GET /health for Render health checks and model warm-up probes.
"""

import asyncio
import io
import json
import logging
import time
from functools import partial
from typing import List

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import require_auth
from api.config import MAX_UPLOAD_SIZE, limiter

logger = structlog.get_logger()
from api.constants import PRIORITY_MAP
from api.resume_parser import extract_text_from_pdf
from api.schemas import (
    CandidateResult,
    ScanDetail,
    ScanHistoryItem,
    ScanResponse,
)
from db.models import Candidate, CandidateSkill, Scan, User
from db.session import get_db
from ml.matcher import (
    calculate_ats_score,
    calculate_component_scores_structured,
    extract_skills,
)
from ml.nlp_utils import clean_texts_batch

log = structlog.get_logger()
router = APIRouter()


# ---------------------------------------------------------------------------
# Health check — required by Render, also used for readiness probing
# ---------------------------------------------------------------------------

@router.get("/health", tags=["ops"])
async def health():
    """
    Lightweight liveness + readiness check.
    Returns 200 once models are loaded (checked via singleton state).
    """
    from ml.nlp_utils import _nlp
    return {
        "status": "ok",
        "models": {
            "spacy":        _nlp is not None,
            "embedder_mode": "tfidf",  # sentence-transformers removed; TF-IDF used
        },
    }


# ---------------------------------------------------------------------------
# Helpers — run blocking ML work off the event loop
# ---------------------------------------------------------------------------

def _run_ml_sync(
    job_description: str,
    raw_resumes: List[str],
    weights: dict,
    required_skills: List[str],
    preferred_skills: List[str],
    experience_cap_years: float,
    min_years_experience: float | None,
    required_degree: str | None,
):
    """
    All CPU-bound / blocking ML work in one function so it can be dispatched
    to a thread-pool executor with a single run_in_executor call.
    """
    # Batch NLP cleaning (single spaCy pipe pass)
    all_texts   = [job_description] + raw_resumes
    all_cleaned = clean_texts_batch(all_texts)
    cleaned_jd  = all_cleaned[0]

    # Pre-compute JD skills once
    jd_required  = set(s.lower() for s in required_skills) | set(extract_skills(job_description))
    jd_preferred = set(s.lower() for s in preferred_skills)

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
    """Extract text from PDF bytes — blocking, safe for executor."""
    from api.resume_parser import extract_text_from_pdf
    return extract_text_from_pdf(io.BytesIO(content))


# ---------------------------------------------------------------------------
# POST /scan/pdf
# ---------------------------------------------------------------------------

@router.post("/scan/pdf", response_model=ScanResponse, status_code=200)
@limiter.limit("10/minute")
async def scan_pdf(
    request: Request,
    # Structured JD fields passed as form fields (multipart form with files)
    job_description:      str   = Form(...),
    required_skills:      str   = Form("[]"),   # JSON array string
    preferred_skills:     str   = Form("[]"),   # JSON array string
    min_years_experience: str   = Form("null"), # JSON null or float
    required_degree:      str   = Form("null"), # JSON null or degree string
    experience_cap_years: float = Form(15.0),
    skills_priority:      str   = Form("High"),
    experience_priority:  str   = Form("Medium"),
    education_priority:   str   = Form("Low"),
    relevance_priority:   str   = Form("Low"),
    files: List[UploadFile] = File(...),
    current_user: User      = Depends(require_auth),
    db: AsyncSession        = Depends(get_db),
):
    t_start = time.perf_counter()

    # --- Parse structured fields ---
    try:
        req_skills  = json.loads(required_skills)
        pref_skills = json.loads(preferred_skills)
        min_yrs     = json.loads(min_years_experience)
        req_degree  = json.loads(required_degree)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Malformed JSON in form field: {e}")

    if len(job_description.strip()) < 20:
        raise HTTPException(status_code=400, detail="Job description is too short to analyze")
    
    if len(job_description) > 10_000:
        raise HTTPException(status_code=400, detail="Job description is too long (max 10,000 characters)")

    if not (1.0 <= experience_cap_years <= 40.0):
        raise HTTPException(status_code=400, detail="experience_cap_years must be between 1 and 40")

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
            detail="Invalid priority. Must be one of: Ignore | Low | Medium | High | Critical",
        )

    if not files:
        raise HTTPException(status_code=400, detail="At least one resume PDF is required")

    # --- Validate files (MIME type) ---
    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} is not a PDF. Only PDF files are accepted."
            )


    # --- Extract PDF text (Parallel — each file in executor) ---
    loop = asyncio.get_event_loop()
    
    async def process_single_file(file: UploadFile):
        # Read in chunks to avoid loading huge files fully into memory before
        # the size check.  Render free tier has only 512 MB RAM total.
        MAX_MB = MAX_UPLOAD_SIZE // (1024 * 1024)
        chunks = []
        total = 0
        CHUNK = 64 * 1024  # 64 KB
        while True:
            chunk = await file.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"{file.filename} exceeds the {MAX_MB} MB limit",
                )
            chunks.append(chunk)
        content = b"".join(chunks)
        
        text = await loop.run_in_executor(None, partial(_extract_pdf_sync, content))
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from {file.filename} (likely image-only PDF)."
            )
        return text, file.filename or "resume.pdf"

    # Run extraction for all files concurrently
    process_results = await asyncio.gather(*[process_single_file(f) for f in files])
    
    raw_resumes = [r[0] for r in process_results]
    filenames   = [r[1] for r in process_results]
    
    for text, fname in zip(raw_resumes, filenames):
        logger.info("pdf_extracted", filename=fname, chars=len(text))

    # --- Run all ML work in a thread pool (non-blocking) ---
    component_scores, ats_scores, jd_required, jd_preferred = await loop.run_in_executor(
        None,
        partial(
            _run_ml_sync,
            job_description,
            raw_resumes,
            weights,
            req_skills,
            pref_skills,
            experience_cap_years,
            min_yrs,
            req_degree,
        ),
    )

    # --- Build result objects ---
    results: List[CandidateResult] = []
    for idx, base in enumerate(component_scores):
        resume_skills  = set(base["resume_skills"])
        matched_skills = jd_required & resume_skills

        results.append(CandidateResult(
            filename=filenames[idx],
            final_score=base["final_score"],
            skills_score=base["skills_score"],
            exp_score=base["exp_score"],
            edu_score=base["edu_score"],
            relevance_score=base["relevance_score"],
            ats_score=ats_scores[idx],
            matched_skills_count=len(matched_skills),
            matched_skills=sorted(matched_skills),
            missing_required_skills=base.get("missing_required_skills", []),
            experience=base.get("experience_str", "0.0 Years"),
            degree=base.get("degree"),
            years_experience=base.get("years_experience"),
            meets_min_experience=base.get("meets_min_experience"),
            meets_degree_req=base.get("meets_degree_req"),
        ))

    results.sort(key=lambda r: r.final_score, reverse=True)
    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

    # --- Persist scan + candidates to database ---
    scan = Scan(
        user_id=current_user.id,
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
        jd_skills_count=len(jd_required),
        processing_time_ms=elapsed_ms,
    )
    db.add(scan)
    await db.flush()  # get scan.id before inserting candidates

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
            ats_score=r.ats_score,
            matched_skills_count=r.matched_skills_count,
            experience=r.experience,
            years_experience=r.years_experience,
            degree=r.degree,
        )
        db.add(cand)
        await db.flush()
        for skill in r.matched_skills:
            db.add(CandidateSkill(candidate_id=cand.id, skill=skill))

    log.info("scan_complete", scan_id=scan.id, candidates=len(results), ms=elapsed_ms,
             user=current_user.email)

    return ScanResponse(
        scan_id=scan.id,
        results=results,
        total_candidates=len(results),
        jd_skills_count=len(jd_required),
        processing_time_ms=elapsed_ms,
        experience_cap_years=experience_cap_years,
    )


# ---------------------------------------------------------------------------
# GET /scans — history list
# ---------------------------------------------------------------------------

@router.get("/scans", response_model=List[ScanHistoryItem], tags=["history"])
async def list_scans(
    limit: int = 20,
    offset: int = 0,
    current_user: User   = Depends(require_auth),
    db: AsyncSession     = Depends(get_db),
):
    """Return a paginated list of past scans for the authenticated user."""
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
            total_candidates=s.total_candidates,
            jd_snippet=s.job_description[:120],
        )
        for s in scans
    ]


# ---------------------------------------------------------------------------
# GET /scans/{scan_id} — full scan detail
# ---------------------------------------------------------------------------

@router.get("/scans/{scan_id}", response_model=ScanDetail, tags=["history"])
async def get_scan(
    scan_id: str,
    current_user: User   = Depends(require_auth),
    db: AsyncSession     = Depends(get_db),
):
    """Return the full results of a past scan by ID."""
    scan: Scan | None = await db.get(Scan, scan_id)
    if scan is None or scan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scan not found.")

    # Load candidates ordered by rank
    cands_result = await db.execute(
        select(Candidate).where(Candidate.scan_id == scan_id).order_by(Candidate.rank)
    )
    candidates = cands_result.scalars().all()

    results: List[CandidateResult] = []
    for c in candidates:
        skills_result = await db.execute(
            select(CandidateSkill).where(CandidateSkill.candidate_id == c.id)
        )
        matched = [s.skill for s in skills_result.scalars().all()]
        results.append(CandidateResult(
            filename=c.filename,
            final_score=c.final_score,
            skills_score=c.skills_score,
            exp_score=c.exp_score,
            edu_score=c.edu_score,
            relevance_score=c.relevance_score,
            ats_score=c.ats_score,
            matched_skills_count=c.matched_skills_count,
            matched_skills=matched,
            missing_required_skills=[],  # not stored per-candidate — re-compute if needed
            experience=c.experience,
            degree=c.degree,
            years_experience=c.years_experience,
        ))

    try:
        req_skills  = json.loads(scan.required_skills  or "[]")
        pref_skills = json.loads(scan.preferred_skills or "[]")
    except json.JSONDecodeError:
        req_skills = pref_skills = []

    return ScanDetail(
        scan_id=scan.id,
        created_at=scan.created_at,
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
