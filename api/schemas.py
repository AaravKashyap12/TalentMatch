"""
Pydantic schemas for TalentMatch API.

Key changes vs original
-----------------------
- JobDescription is now a structured object (required_skills, preferred_skills,
  min_years_experience, required_degree) instead of a raw text blob.
- ScanResponse includes the scan_id so clients can retrieve results later.
- ScanHistoryItem / ScanDetail added for the history endpoints.
- experience_cap_years moved into JobDescription where it semantically belongs.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


Priority = Literal["Ignore", "Low", "Medium", "High", "Critical"]
DegreeLevel = Literal["None", "Associate", "Bachelor", "Master", "PhD"]


# ---------------------------------------------------------------------------
# Job Description — structured input
# ---------------------------------------------------------------------------

class JobDescription(BaseModel):
    """
    Structured job description input.

    Separating required_skills from preferred_skills lets the scoring engine
    weight them differently instead of treating all skills as equal.
    min_years_experience and required_degree replace the blunt experience_cap
    heuristic with explicit recruiter intent.
    """
    text: str = Field(..., min_length=20, description="Full job description text")

    required_skills:   List[str] = Field(default_factory=list,
                        description="Skills a candidate must have")
    preferred_skills:  List[str] = Field(default_factory=list,
                        description="Nice-to-have skills (lower penalty if absent)")

    min_years_experience: Optional[float] = Field(
        default=None, ge=0, le=40,
        description="Minimum years required. Candidates below this are penalised."
    )
    experience_cap_years: float = Field(
        default=15.0, ge=1, le=40,
        description="Years at which exp score reaches 100%."
    )

    required_degree: Optional[DegreeLevel] = Field(
        default=None,
        description="Minimum degree level. Candidates below this are penalised."
    )


class RankingWeights(BaseModel):
    skills:     float = Field(..., ge=0.0, le=1.0)
    experience: float = Field(..., ge=0.0, le=1.0)
    education:  float = Field(..., ge=0.0, le=1.0)
    relevance:  float = Field(..., ge=0.0, le=1.0)


class CandidateResult(BaseModel):
    filename:                str
    final_score:             float
    skills_score:            float
    exp_score:               float
    edu_score:               float
    relevance_score:         float
    ats_score:               float
    matched_skills_count:    int
    matched_skills:          List[str]
    missing_required_skills: List[str]
    experience:              str
    degree:                  Optional[str]   = None
    years_experience:        Optional[float] = None
    meets_min_experience:    Optional[bool]  = None
    meets_degree_req:        Optional[bool]  = None


class ScanResponse(BaseModel):
    scan_id:              str
    results:              List[CandidateResult]
    total_candidates:     int
    jd_skills_count:      int
    processing_time_ms:   float
    experience_cap_years: float


class ScanHistoryItem(BaseModel):
    scan_id:          str
    created_at:       datetime
    total_candidates: int
    jd_snippet:       str


class ScanDetail(BaseModel):
    scan_id:              str
    created_at:           datetime
    job_description:      str
    required_skills:      List[str]
    preferred_skills:     List[str]
    min_years_experience: Optional[float]
    required_degree:      Optional[str]
    experience_cap_years: float
    skills_priority:      str
    experience_priority:  str
    education_priority:   str
    relevance_priority:   str
    total_candidates:     int
    jd_skills_count:      int
    processing_time_ms:   float
    results:              List[CandidateResult]


class RankingPriorities(BaseModel):
    skills:     Priority
    experience: Priority
    education:  Priority
    relevance:  Priority
