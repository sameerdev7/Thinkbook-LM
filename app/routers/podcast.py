import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.deps import get_session_row, get_singletons, get_job_manager, get_current_user
from app.auth.models import User
from app.jobs import JobManager, create_job
from app.models import NotebookSession, Job
from app.pipeline_manager import Singletons
from app.schemas import PodcastScriptRequest, PodcastAudioRequest, JobOut

router = APIRouter(tags=["podcast"])


@router.post("/sessions/{session_id}/podcast/script", response_model=JobOut, status_code=202)
def generate_podcast_script(
    payload: PodcastScriptRequest,
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    singletons: Singletons = Depends(get_singletons),
    job_manager: JobManager = Depends(get_job_manager),
):
    if not singletons.podcast_script_generator:
        raise HTTPException(status_code=400, detail="Podcast generation not configured (OPENAI_API_KEY missing)")

    job = create_job(db, session_row.id, "podcast_script", payload.model_dump())
    job_manager.submit(job.id, "podcast_script", session_row.id, job.input_params)
    return job


@router.post("/sessions/{session_id}/podcast/audio", response_model=JobOut, status_code=202)
def synthesize_podcast_audio(
    payload: PodcastAudioRequest,
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    job_manager: JobManager = Depends(get_job_manager),
):
    job = create_job(db, session_row.id, "podcast_audio", payload.model_dump())
    job_manager.submit(job.id, "podcast_audio", session_row.id, job.input_params)
    return job


@router.get("/podcast/audio/{job_id}/download")
def download_podcast_audio(
    job_id: str,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = (
        db.query(Job)
        .join(NotebookSession, Job.session_id == NotebookSession.id)
        .filter(Job.id == job_id, Job.job_type == "podcast_audio", NotebookSession.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.result or "audio_path" not in job.result:
        raise HTTPException(status_code=409, detail=f"Audio not ready yet (status: {job.status})")

    full_path = os.path.join(settings.OUTPUTS_DIR, job.result["audio_path"])
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Audio file missing on disk")

    return FileResponse(full_path, media_type="audio/wav", filename="podcast.wav")
