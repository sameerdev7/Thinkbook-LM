import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_session_row, get_pipeline_cache
from app.models import NotebookSession, ChatMessage, Source
from app.pipeline_manager import SessionPipelineCache
from app.schemas import QueryRequest, QueryResponse, ChatMessageOut, ChunkPreview

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/sessions/{session_id}/chat", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    pipeline_cache: SessionPipelineCache = Depends(get_pipeline_cache),
):
    pipeline = pipeline_cache.get(session_row)
    if not pipeline.rag_generator:
        raise HTTPException(status_code=400, detail="Chat is not configured (OPENAI_API_KEY missing)")

    has_sources = db.query(Source).filter(Source.session_id == session_row.id).count() > 0
    if not has_sources:
        raise HTTPException(status_code=400, detail="No sources yet -- add a document, audio file, video, or webpage first")

    # generate_response makes a blocking OpenAI call -- keep it off the event loop
    # so other sessions' requests aren't stalled while this one waits on the LLM.
    result = await run_in_threadpool(
        pipeline.rag_generator.generate_response,
        payload.query, payload.max_chunks, 4000, payload.top_k,
    )

    db.add(ChatMessage(session_id=session_row.id, role="user", content=payload.query))
    db.add(ChatMessage(session_id=session_row.id, role="assistant", content=result.response,
                        sources_used=result.sources_used))
    db.commit()

    if pipeline.memory:
        try:
            await run_in_threadpool(pipeline.memory.save_conversation_turn, result)
        except Exception as e:
            logger.warning(f"Memory save failed for session {session_row.id}: {e}")

    return QueryResponse(
        query=result.query, response=result.response,
        sources=result.sources_used, retrieval_count=result.retrieval_count,
    )


@router.get("/sessions/{session_id}/chat", response_model=list[ChatMessageOut])
def get_history(session_row: NotebookSession = Depends(get_session_row), db: DBSession = Depends(get_db)):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_row.id)
        .order_by(ChatMessage.created_at)
        .all()
    )


@router.delete("/sessions/{session_id}/chat", status_code=204)
def clear_chat(
    session_row: NotebookSession = Depends(get_session_row),
    db: DBSession = Depends(get_db),
    pipeline_cache: SessionPipelineCache = Depends(get_pipeline_cache),
):
    db.query(ChatMessage).filter(ChatMessage.session_id == session_row.id).delete()
    db.commit()

    pipeline = pipeline_cache.get(session_row)
    if pipeline.memory:
        try:
            pipeline.memory.clear_session()
        except Exception as e:
            logger.warning(f"Memory clear failed for session {session_row.id}: {e}")
    return None


@router.get("/sessions/{session_id}/chunks/{chunk_id}", response_model=ChunkPreview)
def get_chunk_preview(
    chunk_id: str,
    session_row: NotebookSession = Depends(get_session_row),
    pipeline_cache: SessionPipelineCache = Depends(get_pipeline_cache),
):
    """Backs the citation-tooltip preview shown in the Streamlit UI -- same idea, now an endpoint."""
    pipeline = pipeline_cache.get(session_row)
    chunk_data = pipeline.vector_db.get_chunk_by_id(chunk_id)
    if not chunk_data:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return ChunkPreview(
        chunk_id=chunk_data["id"],
        content=chunk_data["content"][:500],
        source_file=chunk_data["source_file"],
        source_type=chunk_data["source_type"],
        page_number=chunk_data.get("page_number"),
    )
