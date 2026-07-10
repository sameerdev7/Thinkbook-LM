import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.pipeline_manager import Singletons, SessionPipelineCache
from app.jobs import JobManager
from app.cleanup import run_cleanup_loop
from app.rate_limit import limiter
from app.routers import sessions, sources, chat, jobs as jobs_router, podcast, health, auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ThinkbookLM API...")
    Path(settings.MILVUS_DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)

    # Schema is now managed by Alembic migrations, not create_all() -- run
    # `alembic upgrade head` before starting the server. We just verify the
    # `users` table exists (i.e. migrations have been run) rather than
    # silently creating tables here, so a forgotten migration fails loudly
    # at startup instead of causing confusing errors on first request.
    from sqlalchemy import inspect
    from app.database import engine
    if "users" not in inspect(engine).get_table_names():
        raise RuntimeError(
            "Database schema not initialized. Run `alembic upgrade head` before starting the server."
        )

    singletons = Singletons()
    pipeline_cache = SessionPipelineCache(singletons)
    job_manager = JobManager(singletons, pipeline_cache)

    app.state.singletons = singletons
    app.state.pipeline_cache = pipeline_cache
    app.state.job_manager = job_manager

    cleanup_task = asyncio.create_task(run_cleanup_loop(pipeline_cache))

    logger.info("Startup complete.")
    yield

    logger.info("Shutting down...")
    cleanup_task.cancel()
    job_manager.shutdown()
    logger.info("Shutdown complete.")


app = FastAPI(title="ThinkbookLM API", version="2.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(sources.router)
app.include_router(chat.router)
app.include_router(jobs_router.router)
app.include_router(podcast.router)


@app.get("/")
async def root():
    return {"message": "ThinkbookLM API", "version": "2.0.0", "docs": "/docs"}
