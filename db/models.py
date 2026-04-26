"""
SQLAlchemy ORM models for TalentMatch.

Tables
------
  users         — API users (human or service accounts)
  api_keys      — hashed API keys belonging to users
  scans         — one row per /scan/pdf call
  candidates    — one row per resume within a scan
  candidate_skills — many-to-many: skills matched for a candidate
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, ForeignKey, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id         = Column(String(36), primary_key=True, default=_uuid)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    name       = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    free_scans_used = Column(Integer, default=0, nullable=False)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    scans    = relationship("Scan",   back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

class ApiKey(Base):
    __tablename__ = "api_keys"

    id          = Column(String(36), primary_key=True, default=_uuid)
    user_id     = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash    = Column(String(64), unique=True, nullable=False)   # SHA-256 hex
    prefix      = Column(String(8),  nullable=False)                # first 8 chars for display
    name        = Column(String(100), nullable=True)                # e.g. "prod key", "ci key"
    created_at  = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_used   = Column(DateTime(timezone=True), nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey prefix={self.prefix} user={self.user_id}>"


# ---------------------------------------------------------------------------
# Scans (one per /scan/pdf call)
# ---------------------------------------------------------------------------

class Scan(Base):
    __tablename__ = "scans"

    id                   = Column(String(36), primary_key=True, default=_uuid)
    user_id              = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at           = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Job description inputs
    role_title           = Column(String(255), default="Unnamed Scan", nullable=False)
    job_description      = Column(Text, nullable=False)
    required_skills      = Column(Text, nullable=True)   # JSON list
    preferred_skills     = Column(Text, nullable=True)   # JSON list
    min_years_experience = Column(Float, nullable=True)
    required_degree      = Column(String(20), nullable=True)  # None/Bachelor/Master/PhD
    experience_cap_years = Column(Float, default=15.0, nullable=False)

    # Priority weights (stored so results are reproducible)
    skills_priority      = Column(String(20), default="High")
    experience_priority  = Column(String(20), default="Medium")
    education_priority   = Column(String(20), default="Low")
    relevance_priority   = Column(String(20), default="Low")

    # Response metadata
    total_candidates     = Column(Integer, nullable=False)
    top_score            = Column(Float, default=0.0, nullable=False)
    avg_score            = Column(Float, default=0.0, nullable=False)
    jd_skills_count      = Column(Integer, nullable=False)
    processing_time_ms   = Column(Float, nullable=False)

    candidates = relationship("Candidate", back_populates="scan", cascade="all, delete-orphan",
                              order_by="Candidate.rank")

    user = relationship("User", back_populates="scans")

    __table_args__ = (
        Index("ix_scans_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Scan {self.id} candidates={self.total_candidates}>"


# ---------------------------------------------------------------------------
# Candidates (one per resume within a scan)
# ---------------------------------------------------------------------------

class Candidate(Base):
    __tablename__ = "candidates"

    id               = Column(String(36), primary_key=True, default=_uuid)
    scan_id          = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    rank             = Column(Integer, nullable=False)   # 1 = highest score

    filename         = Column(String(255), nullable=False)
    final_score      = Column(Float, nullable=False)
    skills_score     = Column(Float, nullable=False)
    exp_score        = Column(Float, nullable=False)
    edu_score        = Column(Float, nullable=False)
    relevance_score  = Column(Float, nullable=False)
    semantic_overlap_score = Column(Float, nullable=True)
    role_alignment_score = Column(Float, nullable=True)
    ats_score        = Column(Float, nullable=False)

    matched_skills_count = Column(Integer, nullable=False)
    missing_required_skills = Column(Text, nullable=True)  # JSON list of missing required skills
    experience           = Column(String(50), nullable=False)
    years_experience     = Column(Float, nullable=True)
    degree               = Column(String(20), nullable=True)
    primary_backend_language = Column(String(50), nullable=True)
    jd_primary_backend_language = Column(String(50), nullable=True)
    resume_role_family    = Column(String(50), nullable=True)
    jd_role_family        = Column(String(50), nullable=True)
    confidence_level      = Column(String(20), nullable=True)
    hiring_recommendation = Column(String(30), nullable=True)
    ai_overview           = Column(Text, nullable=True)
    score_summary         = Column(Text, nullable=True)
    score_concerns        = Column(Text, nullable=True)  # JSON list
    score_improvements    = Column(Text, nullable=True)  # JSON list

    scan = relationship("Scan", back_populates="candidates")
    skills = relationship("CandidateSkill", back_populates="candidate",
                          cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Candidate {self.filename} score={self.final_score}>"


# ---------------------------------------------------------------------------
# Candidate Skills (matched skills list stored normalised)
# ---------------------------------------------------------------------------

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    skill        = Column(String(100), nullable=False)

    candidate = relationship("Candidate", back_populates="skills")

    __table_args__ = (
        UniqueConstraint("candidate_id", "skill", name="uq_candidate_skill"),
    )
