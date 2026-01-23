from typing import List, Literal

from pydantic import BaseModel, Field


Priority = Literal["Ignore", "Low", "Medium", "High", "Critical"]


class RankingWeights(BaseModel):
    skills: float = Field(..., ge=0.0, le=1.0)
    experience: float = Field(..., ge=0.0, le=1.0)
    education: float = Field(..., ge=0.0, le=1.0)
    relevance: float = Field(..., ge=0.0, le=1.0)


class CandidateResult(BaseModel):
    filename: str
    final_score: float
    skills_score: float
    exp_score: float
    edu_score: float
    relevance_score: float
    ats_score: float
    matched_skills_count: int
    matched_skills: List[str]
    experience: str


class ScanResponse(BaseModel):
    results: List[CandidateResult]


class RankingPriorities(BaseModel):
    skills: Priority
    experience: Priority
    education: Priority
    relevance: Priority
