import asyncio
import logging
import os
from datetime import datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.models import NotebookSession
from app.pipeline_manager import SessionPipelineCache

logger = logging.getLogger(__name__)


def sweep_idle_sessions(pipeline_cache: SessionPipelineCache):
    """One pass: find sessions idle past SESSION_TTL_HOURS and remove them completely
    (Milvus collection + file, and the DB row/cascade)."""
    cutoff = datetime.utcnow() - timedelta(hours=settings.SESSION_TTL_HOURS)
    db = SessionLocal()
    try:
        stale = db.query(NotebookSession).filter(NotebookSession.last_active_at < cutoff).all()
        for session_row in stale:
            logger.info(f"Sweeping idle session {session_row.id} (last active {session_row.last_active_at})")
            try:
                pipeline = pipeline_cache.get(session_row)
                pipeline.vector_db.delete_collection()
            except Exception as e:
                logger.warning(f"Error dropping collection during sweep for {session_row.id}: {e}")
            pipeline_cache.evict(session_row.id)

            # Milvus Lite backs onto a local file -- drop it too, not just the collection.
            try:
                if os.path.exists(session_row.milvus_db_path):
                    os.remove(session_row.milvus_db_path)
            except Exception as e:
                logger.warning(f"Error removing milvus file for {session_row.id}: {e}")

            db.delete(session_row)
        db.commit()
        if stale:
            logger.info(f"Sweep complete: removed {len(stale)} idle session(s)")
    finally:
        db.close()


async def run_cleanup_loop(pipeline_cache: SessionPipelineCache):
    while True:
        await asyncio.sleep(settings.CLEANUP_INTERVAL_MINUTES * 60)
        try:
            sweep_idle_sessions(pipeline_cache)
        except Exception as e:
            logger.error(f"Cleanup sweep failed: {e}")
