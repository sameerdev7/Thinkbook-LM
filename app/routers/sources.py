import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.deps import get_session_row, get_singletons, get_pipeline_cache, get_job_manager
from app.job_tasks import ingest_chunks_to_vector_db
from app.jobs import JobManager, create_job
from app.models import NotebookSession, Job
from app.pipeline_manager import Singletons, SessionPipelineCache
from app.schemas import SourceOut, WebScrapeRequest, YouTubeRequest, JobOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sources"])


def _validate_upload(file: UploadFile, content: bytes):
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large ({size_mb:.1f}MB > {settings.MAX_UPLOAD_SIZE_MB}MB limit)")


@router.post("/sessions/{session_id}/sources/documents", response_model=SourceOut, status_code=201)
async def upload_document(
    session_row: NotebookSession = Depends(get_session_row),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    singletons: Singletons = Depends(get_singletons),
    pipeline_cache: SessionPipelineCache = Depends(get_pipeline_cache),
):
    """
    Documents (pdf/txt/md) are handled synchronously -- parsing + embedding a
    typical document takes low single-digit seconds. Audio, YouTube, and web
    scraping go through the job system instead because they can hang on
    external services for minutes.
    """
    content = await file.read()
    _validate_upload(file, content)

    ext = Path(file.filename).suffix
    if ext.lower() not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail=f"Use /sources/audio for audio files (got {ext})")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        pipeline = pipeline_cache.get(session_row)

        def _process():
            chunks = singletons.doc_processor.process_document(temp_path)
            return ingest_chunks_to_vector_db(
                db, session_row, pipeline, singletons, chunks,
                source_name=file.filename, source_type="document",
                size_label=f"{len(content)/1024:.1f} KB",
            )

        source = await run_in_threadpool(_process)
        return source
    except Exception as e:
        logger.error(f"Document processing failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/sessions/{session_id}/sources/audio", response_model=JobOut, status_code=202)
async def upload_audio(
    session_row: NotebookSession = Depends(get_session_row),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    singletons: Singletons = Depends(get_singletons),
    job_manager: JobManager = Depends(get_job_manager),
):
    if not singletons.audio_transcriber:
        raise HTTPException(status_code=400, detail="Audio transcription not configured (ASSEMBLYAI_API_KEY missing)")

    content = await file.read()
    _validate_upload(file, content)

    ext = Path(file.filename).suffix
    temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}{ext}")
    with open(temp_path, "wb") as f:
        f.write(content)

    job = create_job(db, session_row.id, "audio_upload", {
        "file_path": temp_path,
        "filename": file.filename,
        "size_label": f"{len(content)/1024:.1f} KB",
    })
    job_manager.submit(job.id, "audio_upload", session_row.id, job.input_params)
    return job


@router.post("/sessions/{session_id}/sources/youtube", response_model=JobOut, status_code=202)
def transcribe_youtube(
    payload: YouTubeRequest,
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    singletons: Singletons = Depends(get_singletons),
    job_manager: JobManager = Depends(get_job_manager),
):
    if not singletons.youtube_transcriber:
        raise HTTPException(status_code=400, detail="YouTube transcription not configured (ASSEMBLYAI_API_KEY missing)")

    job = create_job(db, session_row.id, "youtube", {"url": str(payload.url)})
    job_manager.submit(job.id, "youtube", session_row.id, job.input_params)
    return job


@router.post("/sessions/{session_id}/sources/web", response_model=JobOut, status_code=202)
def scrape_web(
    payload: WebScrapeRequest,
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    singletons: Singletons = Depends(get_singletons),
    job_manager: JobManager = Depends(get_job_manager),
):
    if not singletons.web_scraper:
        raise HTTPException(status_code=400, detail="Web scraping not configured (FIRECRAWL_API_KEY missing)")

    job = create_job(db, session_row.id, "web_scrape", {"url": str(payload.url)})
    job_manager.submit(job.id, "web_scrape", session_row.id, job.input_params)
    return job
