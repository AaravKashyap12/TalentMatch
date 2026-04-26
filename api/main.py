import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.config import limiter
from api.routes import router
from api.admin_routes import router as admin_router
from api.session_routes import router as session_router
from db.models import User
from db.session import init_db, AsyncSessionLocal

# ── Supabase (optional) ───────────────────────────────────────────────────────
try:
    from supabase import create_client
    supabase_client = create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_ANON_KEY", ""),
    )
    supabase_admin_client = create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
    )
except ImportError:
    supabase_client = None
    supabase_admin_client = None
    logging.getLogger(__name__).warning("supabase package not installed")

# ── Structured logging ────────────────────────────────────────────────────────
try:
    processors = (
        [structlog.processors.KeyValueRenderer()]
        if os.getenv("DEV_MODE")
        else [structlog.processors.JSONRenderer()]
    )
    structlog.configure(processors=processors)
except Exception:
    structlog.configure(processors=[structlog.processors.JSONRenderer()])

logger = structlog.get_logger()

# NOTE: ML models load lazily on first request (not at startup) to stay within
# small production memory budgets. spaCy en_core_web_sm (~50 MB) loads on first scan.
# TF-IDF (sklearn) is used for semantic similarity — no torch/transformers needed.


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if os.getenv("DEV_MODE", "false").lower() == "true":
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.id == "dev-id"))
            if not result.scalar_one_or_none():
                session.add(User(
                    id="dev-id",
                    email="dev@local",
                    name="Local Developer",
                    is_active=True,
                ))
                await session.commit()
                logger.info("startup: dev-user created")
    logger.info("startup: DB initialised")
    yield
    logger.info("shutdown: complete")


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    origins = {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}
    for origin in list(origins):
        if origin.startswith("http://localhost:"):
            origins.add(origin.replace("http://localhost:", "http://127.0.0.1:"))
        if origin.startswith("http://127.0.0.1:"):
            origins.add(origin.replace("http://127.0.0.1:", "http://localhost:"))
    return sorted(origins)


app = FastAPI(
    title="TalentMatch API",
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.state.supabase = supabase_client
app.state.supabase_admin = supabase_admin_client
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
