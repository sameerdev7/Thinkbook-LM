import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session as DBSession

from app.database import get_db, SessionLocal
from app.deps import get_current_user
from app.auth.models import User
from app.models import Job, NotebookSession
from app.schemas import JobOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["jobs"])


def _get_owned_job(db: DBSession, job_id: str, current_user: User) -> Job:
    job = (
        db.query(Job)
        .join(NotebookSession, Job.session_id == NotebookSession.id)
        .filter(Job.id == job_id, NotebookSession.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: DBSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_owned_job(db, job_id, current_user)


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, current_user: User = Depends(get_current_user)):
    """
    Server-Sent Events progress stream. Polls the DB (not in-memory job state)
    on purpose -- this means it keeps working unchanged even after a future
    move to a multi-worker/Celery setup, since the job status lives in the
    shared DB regardless of which process actually ran the job.
    """
    # Ownership check up front so we don't open a long-lived stream for a job
    # that isn't the caller's.
    db = SessionLocal()
    try:
        _get_owned_job(db, job_id, current_user)
    finally:
        db.close()

    async def event_generator():
        last_payload = None
        while True:
            db = SessionLocal()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
            finally:
                db.close()

            if not job:
                yield {"event": "error", "data": json.dumps({"detail": "Job not found"})}
                return

            payload = {
                "id": job.id, "status": job.status, "progress": job.progress,
                "step_message": job.step_message, "result": job.result, "error": job.error,
            }
            if payload != last_payload:
                yield {"event": "update", "data": json.dumps(payload)}
                last_payload = payload

            if job.status in ("completed", "failed"):
                return

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
