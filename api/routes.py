from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.constants import PRIORITY_MAP
from api.resume_parser import extract_text_from_pdf
from api.schemas import CandidateResult, ScanResponse
from ml.matcher import (
    calculate_ats_score,
    calculate_component_scores,
    extract_experience,
    extract_skills,
)
from ml.nlp_utils import clean_text

router = APIRouter()


@router.post("/scan/pdf", response_model=ScanResponse)
def scan_pdf(
    job_description: str = Form(...),
    skills_priority: str = Form("High"),
    experience_priority: str = Form("Medium"),
    education_priority: str = Form("Low"),
    relevance_priority: str = Form("Low"),
    files: List[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(
            status_code=400,
            detail="At least one resume PDF is required",
        )

    if len(job_description.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Job description is too short to analyze",
        )

    raw_resumes: List[str] = []
    cleaned_resumes: List[str] = []

    for file in files:
        text = extract_text_from_pdf(file.file)

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from {file.filename}",
            )

        raw_resumes.append(text)
        cleaned_resumes.append(clean_text(text))

    cleaned_jd = clean_text(job_description)

    try:
        weights = {
            "skills": PRIORITY_MAP[skills_priority],
            "experience": PRIORITY_MAP[experience_priority],
            "education": PRIORITY_MAP[education_priority],
            "relevance": PRIORITY_MAP[relevance_priority],
        }
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid priority value. Must be one of "
                "Ignore | Low | Medium | High | Critical"
            ),
        )

    component_scores = calculate_component_scores(
        cleaned_jd,
        cleaned_resumes,
        job_description,
        raw_resumes,
        weights,
    )

    jd_skills = set(extract_skills(job_description))
    results: List[CandidateResult] = []

    for index, base in enumerate(component_scores):
        resume_text = raw_resumes[index]

        resume_skills = set(extract_skills(resume_text))
        matched_skills = jd_skills.intersection(resume_skills)

        experience_list = extract_experience(resume_text)
        experience = ", ".join(experience_list) if experience_list else "0 Years"

        ats_score = calculate_ats_score(
            cleaned_resumes[index],
            job_keywords=jd_skills,
        )

        results.append(
            CandidateResult(
                final_score=base["final_score"],
                skills_score=base["skills_score"],
                exp_score=base["exp_score"],
                edu_score=base["edu_score"],
                relevance_score=base["relevance_score"],
                ats_score=ats_score,
                matched_skills_count=len(matched_skills),
                matched_skills=list(matched_skills),
                experience=experience,
            )
        )

    return ScanResponse(results=results)
