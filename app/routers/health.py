from fastapi import APIRouter, Request
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession
from fastapi import Depends

from app.config import settings
from app.database import get_db
from app.models import NotebookSession
from app.schemas import HealthOut, ConfigOut

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthOut)
def health(db: DBSession = Depends(get_db)):
    active_sessions = db.query(func.count(NotebookSession.id)).scalar()
    return HealthOut(status="healthy", active_sessions=active_sessions)


@router.get("/config", response_model=ConfigOut)
def get_config(request: Request):
    features = dict(settings.features)
    # tts availability is only known for certain after first lazy-load attempt;
    # report the optimistic default from settings unless it's already failed.
    singletons = getattr(request.app.state, "singletons", None)
    if singletons is not None:
        features["podcast_audio"] = singletons.tts_available
    return ConfigOut(features=features)
