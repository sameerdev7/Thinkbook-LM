import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class NotebookSession(Base):
    """A user's notebook. Maps 1:1 to a Milvus collection + optional Zep thread."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Where this session's vector data lives. Persisted so we can reconnect
    # after a server restart instead of silently creating a fresh, empty DB.
    milvus_db_path = Column(String(512), nullable=False)
    milvus_collection_name = Column(String(128), nullable=False)
    milvus_index_created = Column(Integer, default=0)  # bool as int (sqlite-friendly)

    created_at = Column(DateTime, default=_now)
    last_active_at = Column(DateTime, default=_now, onupdate=_now)

    sources = relationship("Source", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="session", cascade="all, delete-orphan")
    user = relationship("User", back_populates="sessions")


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)

    name = Column(String(512), nullable=False)
    source_type = Column(String(32), nullable=False)  # document | audio | web | youtube
    size_label = Column(String(64), default="N/A")
    chunk_count = Column(Integer, default=0)

    status = Column(String(32), default="ready")  # processing | ready | failed
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=_now)

    session = relationship("NotebookSession", back_populates="sources")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)

    role = Column(String(16), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    sources_used = Column(JSON, nullable=True)  # list of citation dicts, assistant messages only

    created_at = Column(DateTime, default=_now)

    session = relationship("NotebookSession", back_populates="messages")


class Job(Base):
    """
    Tracks any long-running operation: audio transcription, YouTube transcription,
    podcast script generation, podcast TTS synthesis.

    Status lifecycle: pending -> running -> completed | failed
    """
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)

    job_type = Column(String(32), nullable=False)  # audio_upload | youtube | podcast_script | podcast_audio
    status = Column(String(16), default="pending")  # pending | running | completed | failed
    progress = Column(Float, default=0.0)  # 0-100
    step_message = Column(String(256), default="Queued")

    input_params = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    session = relationship("NotebookSession", back_populates="jobs")
