import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_session_row, get_pipeline_cache, get_current_user
from app.auth.models import User
from app.models import NotebookSession, Source
from app.pipeline_manager import new_milvus_paths, SessionPipelineCache
from app.schemas import SessionCreate, SessionOut, SourceOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sessions"])


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    return (
        db.query(NotebookSession)
        .filter(NotebookSession.user_id == current_user.id)
        .order_by(NotebookSession.last_active_at.desc())
        .all()
    )


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: DBSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_row = NotebookSession(user_id=current_user.id, milvus_db_path="", milvus_collection_name="")
    db.add(session_row)
    db.flush()  # get session_row.id populated before building paths

    db_path, collection_name = new_milvus_paths(session_row.id)
    session_row.milvus_db_path = db_path
    session_row.milvus_collection_name = collection_name
    db.commit()
    db.refresh(session_row)
    return session_row


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_row: NotebookSession = Depends(get_session_row)):
    return session_row


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    pipeline_cache: SessionPipelineCache = Depends(get_pipeline_cache),
):
    # Drop the Milvus collection + close the client before removing the DB row,
    # otherwise the underlying .db file leaks on disk (this is exactly what
    # produced the orphaned milvus_lite_*.db files in the original repo).
    try:
        pipeline = pipeline_cache.get(session_row)
        pipeline.vector_db.delete_collection()
    except Exception as e:
        logger.warning(f"Error dropping collection for session {session_row.id}: {e}")
    pipeline_cache.evict(session_row.id)

    db.delete(session_row)  # cascades to sources/messages/jobs
    db.commit()
    return None


@router.get("/sessions/{session_id}/sources", response_model=list[SourceOut])
def list_sources(session_row: NotebookSession = Depends(get_session_row), db: DBSession = Depends(get_db)):
    return db.query(Source).filter(Source.session_id == session_row.id).order_by(Source.created_at).all()


@router.delete("/sessions/{session_id}/sources/{source_id}", status_code=204)
def delete_source(
    source_id: str,
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    pipeline_cache: SessionPipelineCache = Depends(get_pipeline_cache),
):
    source = db.query(Source).filter(Source.id == source_id, Source.session_id == session_row.id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    pipeline = pipeline_cache.get(session_row)
    try:
        # MilvusClient.delete supports a filter expression; drop every chunk
        # that came from this source file.
        pipeline.vector_db.client.delete(
            collection_name=session_row.milvus_collection_name,
            filter=f'source_file == "{source.name}"',
        )
    except Exception as e:
        logger.warning(f"Error deleting vectors for source {source_id}: {e}")

    db.delete(source)
    db.commit()
    return None
