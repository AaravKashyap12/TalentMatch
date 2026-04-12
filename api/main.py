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

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1 — Init database (creates tables if they don't exist)
    log.info("startup: initialising database")
    from db.session import init_db
    await init_db()
    log.info("startup: database ready")

    # 2 — Warm up spaCy (blocks briefly but happens before first request)
    log.info("startup: warming up spaCy model")
    from ml.nlp_utils import get_nlp
    get_nlp()
    log.info("startup: spaCy ready")

    # 3 — Warm up sentence-transformer / ONNX
    log.info("startup: warming up embedder")
    from ml.matcher import get_embedder
    get_embedder()
    log.info("startup: embedder ready")

    yield
    log.info("shutdown: cleaning up")


def get_cors_origins() -> list[str]:
    origins = os.getenv("CORS_ORIGINS", "")
    if not origins:
        return ["http://localhost:5173", "http://localhost:3000"]
    return [o.strip() for o in origins.split(",") if o.strip()]


app = FastAPI(
    title="TalentMatch API",
    version="2.0.0",
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
