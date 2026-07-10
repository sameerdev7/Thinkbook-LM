"""
SQLAlchemy setup. Sync engine on purpose: every pipeline call downstream
(doc processing, embeddings, Milvus, OpenAI via crewai, AssemblyAI, Firecrawl,
Kokoro) is a blocking sync call anyway. Routes that touch the pipeline run
inside a threadpool (see app/deps.py / app/jobs.py); a sync DB session inside
that same thread is simpler and just as fast as async here.

Swapping DATABASE_URL to postgres:// later requires zero code changes here.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models so they're registered on Base before create_all.
    # auth models first -- NotebookSession.user_id FKs into users.
    from app.auth import models as auth_models  # noqa: F401
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
