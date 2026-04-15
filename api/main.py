import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # Load variables from .env before any other imports

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.config import limiter
from api.routes import router
from api.admin_routes import router as admin_router
from db.session import init_db

# Setup structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer() if not os.getenv("DEV_MODE") else structlog.processors.ConsoleRenderer()
    ],
)
logger = structlog.get_logger()

# NOTE: Models are intentionally NOT loaded at startup.
#
# The Render free tier has a 512 MB RAM cap.  Loading spaCy + sentence-transformers
# at startup consumed ~450 MB before the first request arrived, causing OOM crashes.
#
# sentence-transformers / PyTorch have been removed entirely from requirements.txt.
# ml/matcher.py now uses TF-IDF cosine similarity (~2 MB) as the sole similarity
# engine.  spaCy (en_core_web_sm, ~50 MB) is still used for NER skill extraction and
# loads lazily on the first real request.
#
# The APScheduler keep-alive job has also been removed.  On the free tier it
# re-loaded both heavy models every 14 minutes, permanently pinning ~450 MB of RAM.
# Render's spin-down on inactivity is unavoidable on the free plan; fighting it
# costs more RAM than it saves in latency.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise DB only — models load lazily on first request
    await init_db()
    logger.info("startup: DB initialised; models will lazy-load on first request")
    yield
    logger.info("shutdown: cleaning up")


def get_cors_origins() -> list[str]:
    origins = os.getenv("CORS_ORIGINS", "")
    if not origins:
        return ["http://localhost:5173", "http://localhost:3000"]
    return [o.strip() for o in origins.split(",") if o.strip()]


app = FastAPI(
    title="TalentMatch API",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
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
