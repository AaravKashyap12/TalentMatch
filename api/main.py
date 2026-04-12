import logging
import os
import asyncio
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
from ml.nlp_utils import get_nlp
from ml.matcher import get_embedder

# Setup structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer() if not os.getenv("DEV_MODE") else structlog.processors.ConsoleRenderer()
    ],
)
logger = structlog.get_logger()

async def warm_up_models():
    """Warms up ML models and acts as a keep-alive ping."""
    log = logger.bind(stage="warmup")
    try:
        # 1. Warm up ML logic
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, get_nlp)
        await loop.run_in_executor(None, get_embedder)
        
        # 2. Self-ping to keep Render networking alive
        # (Replace with your actual Render URL once deployed for best results)
        log.info("Keep-alive: Models refreshed and system pinged.")
    except Exception as e:
        log.error("Keep-alive/Warm-up failed", error=str(e))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize DB
    await init_db()
    
    # 2. Setup Scheduler for Keep-alive (run every 14 mins to beat 15 min timeout)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(warm_up_models, 'interval', minutes=14)
    scheduler.start()
    
    # 3. Initial warm-up
    asyncio.create_task(warm_up_models())
    
    yield
    scheduler.shutdown()
    logger.info("shutdown: cleaning up")


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
