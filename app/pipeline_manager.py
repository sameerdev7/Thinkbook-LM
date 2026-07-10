"""
Manages instances of the pipeline classes from src/.

Key design decision vs. the original app.py/api.py: most pipeline components
are STATELESS w.r.t. session (DocumentProcessor, EmbeddingGenerator,
AudioTranscriber, YouTubeTranscriber, WebScraper, PodcastScriptGenerator,
PodcastTTSGenerator all just take params per call). Recreating them per
session -- as the original code did -- means reloading the embedding model
and the Kokoro TTS model on every single session. Both are expensive
(seconds to tens of seconds). So:

  - Singletons: created once at app startup, shared across all sessions.
  - Per-session: only MilvusVectorDB (own file + collection), RAGGenerator
    (wraps the shared embedding generator + this session's vector db),
    and NotebookMemoryLayer (bound to a Zep thread id) are per-session.

Per-session objects are cached in memory but are always re-derivable from
the DB row (milvus_db_path/collection_name), so a server restart just means
the first request after restart pays a small reconnect cost instead of
losing data.
"""
import logging
import os
import threading
from pathlib import Path
from typing import Dict, Optional

from app.config import settings
from app.models import NotebookSession

logger = logging.getLogger(__name__)

# --- Pipeline imports (unchanged from src/) ---
from src.document_processing.doc_processor import DocumentProcessor
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vector_database.milvus_vector_db import MilvusVectorDB
from src.generation.rag import RAGGenerator
from src.memory.memory_layer import NotebookMemoryLayer
from src.audio_processing.audio_transcriber import AudioTranscriber
from src.audio_processing.youtube_transcriber import YouTubeTranscriber
from src.web_scraping.web_scraper import WebScraper
from src.podcast.script_generator import PodcastScriptGenerator
from src.podcast.text_to_speech import PodcastTTSGenerator


class Singletons:
    """Created once in main.py's lifespan startup, stashed on app.state."""

    def __init__(self):
        logger.info("Initializing shared pipeline singletons...")

        self.doc_processor = DocumentProcessor()
        self.embedding_generator = EmbeddingGenerator()

        self.audio_transcriber: Optional[AudioTranscriber] = (
            AudioTranscriber(settings.ASSEMBLYAI_API_KEY) if settings.ASSEMBLYAI_API_KEY else None
        )
        self.youtube_transcriber: Optional[YouTubeTranscriber] = (
            YouTubeTranscriber(settings.ASSEMBLYAI_API_KEY) if settings.ASSEMBLYAI_API_KEY else None
        )
        self.web_scraper: Optional[WebScraper] = (
            WebScraper(settings.FIRECRAWL_API_KEY) if settings.FIRECRAWL_API_KEY else None
        )
        self.podcast_script_generator: Optional[PodcastScriptGenerator] = (
            PodcastScriptGenerator(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        )

        # Kokoro TTS is the heaviest load (model weights) and not everyone
        # needs podcast audio -- lazy-load on first use, guarded by a lock.
        self._tts_generator: Optional[PodcastTTSGenerator] = None
        self._tts_lock = threading.Lock()
        self._tts_load_failed = False

        logger.info(
            "Singletons ready. audio=%s youtube=%s web=%s podcast_script=%s",
            bool(self.audio_transcriber), bool(self.youtube_transcriber),
            bool(self.web_scraper), bool(self.podcast_script_generator),
        )

    @property
    def tts_generator(self) -> Optional[PodcastTTSGenerator]:
        if self._tts_generator is not None or self._tts_load_failed:
            return self._tts_generator
        with self._tts_lock:
            if self._tts_generator is None and not self._tts_load_failed:
                try:
                    logger.info("Lazy-loading Kokoro TTS model (first podcast-audio request)...")
                    self._tts_generator = PodcastTTSGenerator()
                except Exception as e:
                    logger.warning(f"TTS unavailable: {e}")
                    self._tts_load_failed = True
        return self._tts_generator

    @property
    def tts_available(self) -> bool:
        """Non-blocking check for /config -- does not trigger the lazy load."""
        if self._tts_generator is not None:
            return True
        if self._tts_load_failed:
            return False
        return True  # optimistic; real answer known once first request lazy-loads it


class SessionPipeline:
    """Per-session bundle: vector_db, rag_generator, memory (optional)."""

    def __init__(self, session_row: NotebookSession, singletons: Singletons):
        self.vector_db = MilvusVectorDB(
            db_path=session_row.milvus_db_path,
            collection_name=session_row.milvus_collection_name,
            embedding_dim=singletons.embedding_generator.get_embedding_dimension(),
        )
        self.rag_generator = RAGGenerator(
            embedding_generator=singletons.embedding_generator,
            vector_db=self.vector_db,
            openai_api_key=settings.OPENAI_API_KEY,
        ) if settings.OPENAI_API_KEY else None

        self.memory: Optional[NotebookMemoryLayer] = None
        if settings.ZEP_API_KEY:
            try:
                self.memory = NotebookMemoryLayer(
                    user_id=session_row.user_id,
                    session_id=session_row.id,
                    zep_api_key=settings.ZEP_API_KEY,
                    create_new_session=False,  # reuse thread if it already exists (e.g. after restart)
                )
            except Exception as e:
                logger.warning(f"Memory layer unavailable for session {session_row.id}: {e}")

    def close(self):
        try:
            self.vector_db.close()
        except Exception as e:
            logger.warning(f"Error closing vector db: {e}")


class SessionPipelineCache:
    """
    In-memory cache of SessionPipeline objects, keyed by session id.
    Thread-safe. Rebuilds transparently from the DB row if evicted or
    if the process just restarted.
    """

    def __init__(self, singletons: Singletons):
        self._singletons = singletons
        self._cache: Dict[str, SessionPipeline] = {}
        self._lock = threading.Lock()

    def get(self, session_row: NotebookSession) -> SessionPipeline:
        with self._lock:
            pipeline = self._cache.get(session_row.id)
            if pipeline is None:
                logger.info(f"Building pipeline for session {session_row.id}")
                pipeline = SessionPipeline(session_row, self._singletons)
                self._cache[session_row.id] = pipeline
            return pipeline

    def evict(self, session_id: str):
        with self._lock:
            pipeline = self._cache.pop(session_id, None)
        if pipeline:
            pipeline.close()


def new_milvus_paths(session_id: str) -> tuple[str, str]:
    """Deterministic, collision-free per-session Milvus file + collection name."""
    Path(settings.MILVUS_DATA_DIR).mkdir(parents=True, exist_ok=True)
    short = session_id.replace("-", "")[:12]
    db_path = os.path.join(settings.MILVUS_DATA_DIR, f"session_{short}.db")
    collection_name = f"collection_{short}"
    return db_path, collection_name
