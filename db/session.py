"""
Database session factory for TalentMatch.

Uses SQLite for local dev (zero-config) and Postgres on Render/production.
Set DATABASE_URL env var to switch:
  SQLite  (default): sqlite+aiosqlite:///./talentmatch.db
  Postgres:          postgresql+asyncpg://user:pass@host/dbname
"""

import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

# ---------------------------------------------------------------------------
# Engine — async driver in both cases
# ---------------------------------------------------------------------------

_RAW_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./talentmatch.db")

# Render injects DATABASE_URL as postgres://... (old format); SQLAlchemy 2
# requires postgresql+asyncpg://...
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
