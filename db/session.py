"""
Database session factory for TalentMatch.

Uses SQLite for local dev (zero-config) and Postgres in production.
Set DATABASE_URL env var to switch:
  SQLite  (default): sqlite+aiosqlite:///./talentmatch.db
  Postgres:          postgresql+asyncpg://user:pass@host/dbname
"""

import os
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

# ---------------------------------------------------------------------------
# Engine — async driver in both cases
# ---------------------------------------------------------------------------

_RAW_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./talentmatch.db")

# Some platforms inject DATABASE_URL as postgres://... (old format);
# SQLAlchemy 2 requires postgresql+asyncpg://...
if _RAW_URL.startswith("postgres://"):
    _RAW_URL = _RAW_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif _RAW_URL.startswith("postgresql://") and "+asyncpg" not in _RAW_URL:
    _RAW_URL = _RAW_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

_CONNECT_ARGS = {}
if _RAW_URL.startswith("sqlite"):
    # SQLite needs check_same_thread=False for async use
    _CONNECT_ARGS = {"check_same_thread": False}

engine = create_async_engine(
    _RAW_URL,
    connect_args=_CONNECT_ARGS,
    echo=os.getenv("DB_ECHO", "").lower() in ("1", "true"),
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Dependency for FastAPI routes
# ---------------------------------------------------------------------------

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Create all tables (called from lifespan)
# ---------------------------------------------------------------------------

async def init_db():
    """Create all tables and patch missing scan columns for existing databases."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            dialect = conn.dialect.name
            if dialect == "sqlite":
                user_pragma = await conn.execute(text("PRAGMA table_info(users)"))
                existing_user_columns = {row[1] for row in user_pragma.fetchall()}
                pragma = await conn.execute(text("PRAGMA table_info(scans)"))
                existing_columns = {row[1] for row in pragma.fetchall()}
                cand_pragma = await conn.execute(text("PRAGMA table_info(candidates)"))
                existing_candidate_columns = {row[1] for row in cand_pragma.fetchall()}
            else:
                user_col_query = await conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                """))
                existing_user_columns = {row[0] for row in user_col_query.fetchall()}
                col_query = await conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'scans'
                """))
                existing_columns = {row[0] for row in col_query.fetchall()}
                cand_col_query = await conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'candidates'
                """))
                existing_candidate_columns = {row[0] for row in cand_col_query.fetchall()}

            if "free_scans_used" not in existing_user_columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN free_scans_used INTEGER DEFAULT 0 NOT NULL"))
            if "role_title" not in existing_columns:
                await conn.execute(text("ALTER TABLE scans ADD COLUMN role_title VARCHAR(255) DEFAULT 'Unnamed Scan'"))
            if "top_score" not in existing_columns:
                await conn.execute(text("ALTER TABLE scans ADD COLUMN top_score FLOAT DEFAULT 0"))
            if "avg_score" not in existing_columns:
                await conn.execute(text("ALTER TABLE scans ADD COLUMN avg_score FLOAT DEFAULT 0"))
            if "primary_backend_language" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN primary_backend_language VARCHAR(50)"))
            if "jd_primary_backend_language" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN jd_primary_backend_language VARCHAR(50)"))
            if "semantic_overlap_score" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN semantic_overlap_score FLOAT"))
            if "role_alignment_score" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN role_alignment_score FLOAT"))
            if "resume_role_family" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN resume_role_family VARCHAR(50)"))
            if "jd_role_family" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN jd_role_family VARCHAR(50)"))
            if "confidence_level" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN confidence_level VARCHAR(20)"))
            if "hiring_recommendation" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN hiring_recommendation VARCHAR(30)"))
            if "ai_overview" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN ai_overview TEXT"))
            if "score_summary" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN score_summary TEXT"))
            if "score_concerns" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN score_concerns TEXT"))
            if "score_improvements" not in existing_candidate_columns:
                await conn.execute(text("ALTER TABLE candidates ADD COLUMN score_improvements TEXT"))

            await conn.execute(text("""
                UPDATE users
                SET free_scans_used = (
                    SELECT COUNT(*)
                    FROM scans
                    WHERE scans.user_id = users.id
                )
                WHERE free_scans_used IS NULL OR free_scans_used = 0
            """))
            await conn.execute(text("UPDATE scans SET role_title = COALESCE(role_title, 'Unnamed Scan')"))
            await conn.execute(text("UPDATE scans SET top_score = COALESCE(top_score, 0)"))
            await conn.execute(text("UPDATE scans SET avg_score = COALESCE(avg_score, 0)"))
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("init_db failed", error=str(e)[:200])
        raise
