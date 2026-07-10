"""
In-process job execution.

Design note (see the earlier discussion on scaling): this ONLY works
correctly with a single uvicorn worker, because the ThreadPoolExecutor here
lives in one process's memory. If you later move to multiple workers or
Celery/RQ, the interface (`submit`, and Job rows in the DB) stays the same --
only this file's internals change to push onto a shared queue instead of a
local executor.
"""
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import SessionLocal
from app.models import Job, NotebookSession
from app.pipeline_manager import Singletons, SessionPipelineCache
from app.job_tasks import JOB_HANDLERS

logger = logging.getLogger(__name__)


def create_job(db: DBSession, session_id: str, job_type: str, params: Dict[str, Any]) -> Job:
    """Create the Job row. Caller still needs to call JobManager.submit(...) to actually run it."""
    job = Job(session_id=session_id, job_type=job_type, status="pending", step_message="Queued", input_params=params)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class JobManager:
    def __init__(self, singletons: Singletons, pipeline_cache: SessionPipelineCache):
        self._executor = ThreadPoolExecutor(max_workers=settings.JOB_THREAD_POOL_SIZE, thread_name_prefix="job")
        self._singletons = singletons
        self._pipeline_cache = pipeline_cache

    def submit(self, job_id: str, job_type: str, session_id: str, params: Dict[str, Any]):
        if job_type not in JOB_HANDLERS:
            raise ValueError(f"Unknown job type: {job_type}")
        self._executor.submit(self._run, job_id, job_type, session_id, params)

    def _run(self, job_id: str, job_type: str, session_id: str, params: Dict[str, Any]):
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            session_row = db.query(NotebookSession).filter(NotebookSession.id == session_id).first()
            if not job or not session_row:
                logger.error(f"Job {job_id} or session {session_id} vanished before it could run")
                return

            job.status = "running"
            job.step_message = "Starting..."
            db.commit()

            pipeline = self._pipeline_cache.get(session_row)
            handler = JOB_HANDLERS[job_type]

            try:
                result = handler(db, job, session_row, pipeline, self._singletons, params)
                job.result = result
                job.status = "completed"
                job.progress = 100
                job.step_message = "Done"
                db.commit()
            except Exception as e:
                logger.error(f"Job {job_id} ({job_type}) failed: {e}\n{traceback.format_exc()}")
                job.status = "failed"
                job.error = str(e)
                db.commit()
        finally:
            db.close()

    def shutdown(self):
        self._executor.shutdown(wait=True)
