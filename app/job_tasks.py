"""
The actual work each Job type does. Runs inside a worker thread (see
app/jobs.py's JobManager) -- never on the event loop. Each function takes
its own DB session because SQLAlchemy sessions aren't safe to share
across threads.

Progress is coarse-grained (a handful of checkpoints per job) rather than
per-chunk/per-segment. Getting true per-segment progress out of
transcribe_audio / generate_podcast_audio would need a small callback hook
added to src/audio_processing/audio_transcriber.py and
src/podcast/text_to_speech.py -- straightforward to add later if the
progress bar granularity matters to you, skipped here to avoid touching
your working pipeline code.
"""
import logging
import os
from pathlib import Path
from typing import Dict, Any

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import Job, Source
from app.pipeline_manager import Singletons, SessionPipeline

logger = logging.getLogger(__name__)


def _set_progress(db: DBSession, job: Job, progress: float, message: str, status: str = "running"):
    job.progress = progress
    job.step_message = message
    job.status = status
    db.commit()
    logger.info(f"[job {job.id}] {progress:.0f}% - {message}")


def ingest_chunks_to_vector_db(db, session_row, pipeline: SessionPipeline, singletons: Singletons,
                                  chunks, source_name: str, source_type: str, size_label: str) -> Source:
    """Shared tail-end: embed chunks, insert into Milvus, create Source row."""
    if not chunks:
        raise ValueError("No content was extracted -- nothing to index.")

    for c in chunks:
        c.source_file = source_name

    embedded = singletons.embedding_generator.generate_embeddings(chunks)

    is_first_source = db.query(Source).filter(Source.session_id == session_row.id).count() == 0
    if is_first_source or not session_row.milvus_index_created:
        pipeline.vector_db.create_index()
        session_row.milvus_index_created = 1
        db.add(session_row)

    pipeline.vector_db.insert_embeddings(embedded)

    source = Source(
        session_id=session_row.id,
        name=source_name,
        source_type=source_type,
        size_label=size_label,
        chunk_count=len(chunks),
        status="ready",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def run_audio_upload_job(db: DBSession, job: Job, session_row, pipeline: SessionPipeline,
                          singletons: Singletons, params: Dict[str, Any]) -> Dict[str, Any]:
    file_path = params["file_path"]
    filename = params["filename"]
    size_label = params["size_label"]

    if not singletons.audio_transcriber:
        raise RuntimeError("Audio transcription is not configured (ASSEMBLYAI_API_KEY missing).")

    try:
        _set_progress(db, job, 10, "Transcribing audio...")
        chunks = singletons.audio_transcriber.transcribe_audio(file_path)

        _set_progress(db, job, 60, "Generating embeddings...")
        source = ingest_chunks_to_vector_db(
            db, session_row, pipeline, singletons, chunks,
            source_name=filename, source_type="audio", size_label=size_label,
        )

        _set_progress(db, job, 100, "Done", status="completed")
        return {"source_id": source.id, "chunks_created": source.chunk_count}
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)


def run_youtube_job(db: DBSession, job: Job, session_row, pipeline: SessionPipeline,
                     singletons: Singletons, params: Dict[str, Any]) -> Dict[str, Any]:
    url = params["url"]

    if not singletons.youtube_transcriber:
        raise RuntimeError("YouTube transcription is not configured (ASSEMBLYAI_API_KEY missing).")

    _set_progress(db, job, 10, "Downloading audio...")
    _set_progress(db, job, 25, "Transcribing (this can take a few minutes for long videos)...")
    chunks = singletons.youtube_transcriber.transcribe_youtube_video(url)

    _set_progress(db, job, 70, "Generating embeddings...")
    source = ingest_chunks_to_vector_db(
        db, session_row, pipeline, singletons, chunks,
        source_name=f"YouTube: {url}", source_type="youtube", size_label="N/A",
    )

    _set_progress(db, job, 100, "Done", status="completed")
    return {"source_id": source.id, "chunks_created": source.chunk_count}


def run_web_scrape_job(db: DBSession, job: Job, session_row, pipeline: SessionPipeline,
                        singletons: Singletons, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Web scraping is usually fast, but Firecrawl can hang on slow sites, so it
    still goes through the job system rather than blocking a request.
    """
    url = params["url"]

    if not singletons.web_scraper:
        raise RuntimeError("Web scraping is not configured (FIRECRAWL_API_KEY missing).")

    _set_progress(db, job, 20, "Scraping page...")
    chunks = singletons.web_scraper.scrape_url(url)

    _set_progress(db, job, 70, "Generating embeddings...")
    title = chunks[0].source_file if chunks else url
    source = ingest_chunks_to_vector_db(
        db, session_row, pipeline, singletons, chunks,
        source_name=title, source_type="web", size_label="N/A",
    )

    _set_progress(db, job, 100, "Done", status="completed")
    return {"source_id": source.id, "chunks_created": source.chunk_count}


def run_podcast_script_job(db: DBSession, job: Job, session_row, pipeline: SessionPipeline,
                            singletons: Singletons, params: Dict[str, Any]) -> Dict[str, Any]:
    if not singletons.podcast_script_generator:
        raise RuntimeError("Podcast script generation is not configured (OPENAI_API_KEY missing).")
    if not pipeline.rag_generator:
        raise RuntimeError("RAG is not configured (OPENAI_API_KEY missing).")

    style = params.get("style", "conversational")
    duration = params.get("duration", "10 minutes")
    source_name = params.get("source_name")

    _set_progress(db, job, 20, "Summarizing sources...")
    summary_result = pipeline.rag_generator.generate_summary(max_chunks=15, summary_length="long")

    _set_progress(db, job, 60, "Writing script...")
    script = singletons.podcast_script_generator.generate_script_from_text(
        text_content=summary_result.response,
        source_name=source_name or "Knowledge Base",
        podcast_style=style,
        target_duration=duration,
    )

    _set_progress(db, job, 100, "Done", status="completed")
    return {
        "script": script.script,
        "total_lines": script.total_lines,
        "estimated_duration": script.estimated_duration,
        "source_document": script.source_document,
    }


def run_podcast_audio_job(db: DBSession, job: Job, session_row, pipeline: SessionPipeline,
                           singletons: Singletons, params: Dict[str, Any]) -> Dict[str, Any]:
    from src.podcast.script_generator import PodcastScript

    tts = singletons.tts_generator
    if tts is None:
        raise RuntimeError("TTS engine failed to load (Kokoro not available on this server).")

    script = PodcastScript(
        script=params["script"],
        source_document=params.get("source_document", "Generated"),
        total_lines=len(params["script"]),
        estimated_duration=params.get("estimated_duration", "10 minutes"),
    )

    output_dir = os.path.join(settings.OUTPUTS_DIR, "podcasts", job.id)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    _set_progress(db, job, 15, f"Synthesizing {script.total_lines} lines of dialogue...")
    output_files = tts.generate_podcast_audio(script, output_dir=output_dir, combine_audio=True)

    combined = next((f for f in output_files if "complete" in f), None)
    if not combined:
        raise RuntimeError("TTS finished but no combined audio file was produced.")

    _set_progress(db, job, 100, "Done", status="completed")
    # Path is relative to OUTPUTS_DIR so the API layer can build a download URL
    return {"audio_path": os.path.relpath(combined, settings.OUTPUTS_DIR)}


# Registry: job_type -> callable
JOB_HANDLERS = {
    "audio_upload": run_audio_upload_job,
    "youtube": run_youtube_job,
    "web_scrape": run_web_scrape_job,
    "podcast_script": run_podcast_script_job,
    "podcast_audio": run_podcast_audio_job,
}
