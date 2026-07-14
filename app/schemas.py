from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, ConfigDict


# ---------- Sessions ----------

class SessionCreate(BaseModel):
    name: Optional[str] = None  # defaults to "Untitled notebook" server-side if omitted


class SessionUpdate(BaseModel):
    name: str


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    name: str
    created_at: datetime
    last_active_at: datetime


# ---------- Sources ----------

class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    source_type: str
    size_label: str
    chunk_count: int
    status: str
    error: Optional[str] = None
    created_at: datetime


class WebScrapeRequest(BaseModel):
    url: HttpUrl


# ---------- Chat ----------

class QueryRequest(BaseModel):
    query: str
    max_chunks: int = 8
    top_k: int = 10


class CitationOut(BaseModel):
    reference: str
    source_file: str
    source_type: str
    page_number: Optional[int] = None
    chunk_id: str
    relevance_score: float


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    content: str
    sources_used: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class QueryResponse(BaseModel):
    query: str
    response: str
    sources: List[Dict[str, Any]]
    retrieval_count: int


class ChunkPreview(BaseModel):
    chunk_id: str
    content: str
    source_file: str
    source_type: str
    page_number: Optional[int] = None


# ---------- Jobs ----------

class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_type: str
    status: str
    progress: float
    step_message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class YouTubeRequest(BaseModel):
    url: HttpUrl


class PodcastScriptRequest(BaseModel):
    style: str = "conversational"  # conversational | educational | interview | debate
    duration: str = "10 minutes"   # 5|10|15|20 minutes
    source_name: Optional[str] = None  # if omitted, summarizes across all sources


class PodcastAudioRequest(BaseModel):
    script: List[Dict[str, str]]
    source_document: str = "Generated"
    estimated_duration: str = "10 minutes"


# ---------- Misc ----------

class ConfigOut(BaseModel):
    features: Dict[str, bool]


class HealthOut(BaseModel):
    status: str
    active_sessions: int
