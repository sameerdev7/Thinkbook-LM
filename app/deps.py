from datetime import datetime

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import NotebookSession
from app.auth.models import User
from app.auth import security
from app.pipeline_manager import Singletons, SessionPipelineCache
from app.jobs import JobManager

# re-export for convenience
__all__ = ["get_db", "get_session_row", "get_singletons", "get_pipeline_cache", "get_job_manager", "get_current_user"]

_bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: DBSession = Depends(get_db),
) -> User:
    try:
        user_id = security.decode_access_token(credentials.credentials)
    except security.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=str(e), headers={"WWW-Authenticate": "Bearer"})

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled", headers={"WWW-Authenticate": "Bearer"})
    return user


def get_singletons(request: Request) -> Singletons:
    return request.app.state.singletons


def get_pipeline_cache(request: Request) -> SessionPipelineCache:
    return request.app.state.pipeline_cache


def get_job_manager(request: Request) -> JobManager:
    return request.app.state.job_manager


def get_session_row(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotebookSession:
    session_row = db.query(NotebookSession).filter(NotebookSession.id == session_id).first()
    # 404 (not 403) whether the session doesn't exist or just isn't the caller's --
    # confirming a session_id belongs to someone else is its own small leak.
    if not session_row or session_row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    session_row.last_active_at = datetime.utcnow()
    db.commit()
    return session_row
