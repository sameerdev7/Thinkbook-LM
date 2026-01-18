from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import tempfile
import os
import uuid
import logging
from pathlib import Path
import json

# Import your pipeline components
from src.document_processing.doc_processor import DocumentProcessor
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vector_database.milvus_vector_db import MilvusVectorDB
from src.generation.rag import RAGGenerator, RAGResult
from src.memory.memory_layer import NotebookMemoryLayer
from src.audio_processing.audio_transcriber import AudioTranscriber
from src.audio_processing.youtube_transcriber import YouTubeTranscriber
from src.web_scraping.web_scraper import WebScraper
from src.podcast.script_generator import PodcastScriptGenerator
from src.podcast.text_to_speech import PodcastTTSGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="ThinkbookLM API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class QueryRequest(BaseModel):
    query: str
    session_id: str
    max_chunks: int = 8

class WebScrapeRequest(BaseModel):
    url: HttpUrl
    session_id: str

class YouTubeRequest(BaseModel):
    url: HttpUrl
    session_id: str

class PodcastRequest(BaseModel):
    session_id: str
    style: str = "conversational"
    duration: str = "10 minutes"
    source_name: Optional[str] = None

class SessionCreate(BaseModel):
    user_id: str = "default_user"

class ChatHistoryResponse(BaseModel):
    messages: List[Dict[str, Any]]
    session_id: str

# Global session storage (in production, use Redis or database)
sessions: Dict[str, Dict[str, Any]] = {}

# Helper Functions
def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """Get existing session or create new pipeline"""
    if session_id not in sessions:
        try:
            # Initialize pipeline components
            doc_processor = DocumentProcessor()
            embedding_generator = EmbeddingGenerator()
            vector_db = MilvusVectorDB(
                db_path=f"./milvus_session_{session_id[:8]}.db",
                collection_name=f"collection_{session_id[:8]}"
            )
            rag_generator = RAGGenerator(
                embedding_generator=embedding_generator,
                vector_db=vector_db,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # Optional components
            audio_transcriber = AudioTranscriber(os.getenv("ASSEMBLYAI_API_KEY")) if os.getenv("ASSEMBLYAI_API_KEY") else None
            youtube_transcriber = YouTubeTranscriber(os.getenv("ASSEMBLYAI_API_KEY")) if os.getenv("ASSEMBLYAI_API_KEY") else None
            web_scraper = WebScraper(os.getenv("FIRECRAWL_API_KEY")) if os.getenv("FIRECRAWL_API_KEY") else None
            podcast_gen = PodcastScriptGenerator(os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
            
            tts_gen = None
            try:
                tts_gen = PodcastTTSGenerator()
            except:
                logger.warning("TTS not available")
            
            memory = NotebookMemoryLayer(
                user_id="api_user",
                session_id=session_id,
                create_new_session=True
            ) if os.getenv("ZEP_API_KEY") else None
            
            sessions[session_id] = {
                'pipeline': {
                    'doc_processor': doc_processor,
                    'embedding_generator': embedding_generator,
                    'vector_db': vector_db,
                    'rag_generator': rag_generator,
                    'audio_transcriber': audio_transcriber,
                    'youtube_transcriber': youtube_transcriber,
                    'web_scraper': web_scraper,
                    'podcast_script_generator': podcast_gen,
                    'podcast_tts_generator': tts_gen,
                    'memory': memory
                },
                'sources': [],
                'chat_history': [],
                'created_at': str(uuid.uuid4())
            }
            
            logger.info(f"Created new session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")
    
    return sessions[session_id]

# API Endpoints

@app.get("/")
async def root():
    return {"message": "ThinkbookLM API", "version": "1.0.0"}

@app.post("/sessions/create")
async def create_session(data: SessionCreate):
    """Create a new session"""
    session_id = str(uuid.uuid4())
    get_or_create_session(session_id)
    return {"session_id": session_id, "user_id": data.user_id}

@app.get("/sessions/{session_id}/sources")
async def get_sources(session_id: str):
    """Get all sources for a session"""
    session = get_or_create_session(session_id)
    return {"sources": session['sources'], "count": len(session['sources'])}

@app.post("/documents/upload")
async def upload_document(
    session_id: str,
    file: UploadFile = File(...)
):
    """Upload and process a document"""
    session = get_or_create_session(session_id)
    pipeline = session['pipeline']
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
        content = await file.read()
        tmp.write(content)
        temp_path = tmp.name
    
    try:
        # Process based on file type
        if file.content_type and file.content_type.startswith('audio/'):
            if not pipeline['audio_transcriber']:
                raise HTTPException(status_code=400, detail="Audio transcription not configured")
            chunks = pipeline['audio_transcriber'].transcribe_audio(temp_path)
            source_type = "audio"
        else:
            chunks = pipeline['doc_processor'].process_document(temp_path)
            source_type = "document"
        
        # Update source file names
        for chunk in chunks:
            chunk.source_file = file.filename
        
        # Generate embeddings and store
        if chunks:
            embedded = pipeline['embedding_generator'].generate_embeddings(chunks)
            
            # Create index if first source
            if not session['sources']:
                pipeline['vector_db'].create_index()
            
            pipeline['vector_db'].insert_embeddings(embedded)
            
            # Add to sources list
            session['sources'].append({
                'name': file.filename,
                'type': source_type,
                'size': f"{len(content)/1024:.1f} KB",
                'chunks': len(chunks),
                'uploaded_at': str(uuid.uuid4())
            })
            
            return {
                "success": True,
                "filename": file.filename,
                "chunks_created": len(chunks),
                "source_type": source_type
            }
        else:
            raise HTTPException(status_code=400, detail="No content extracted from file")
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(temp_path)

@app.post("/web/scrape")
async def scrape_website(request: WebScrapeRequest):
    """Scrape and process a website"""
    session = get_or_create_session(request.session_id)
    pipeline = session['pipeline']
    
    if not pipeline['web_scraper']:
        raise HTTPException(status_code=400, detail="Web scraping not configured")
    
    try:
        chunks = pipeline['web_scraper'].scrape_url(str(request.url))
        
        if chunks:
            embedded = pipeline['embedding_generator'].generate_embeddings(chunks)
            
            if not session['sources']:
                pipeline['vector_db'].create_index()
            
            pipeline['vector_db'].insert_embeddings(embedded)
            
            session['sources'].append({
                'name': str(request.url),
                'type': 'web',
                'size': 'N/A',
                'chunks': len(chunks),
                'uploaded_at': str(uuid.uuid4())
            })
            
            return {
                "success": True,
                "url": str(request.url),
                "chunks_created": len(chunks)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/youtube/transcribe")
async def transcribe_youtube(request: YouTubeRequest):
    """Transcribe a YouTube video"""
    session = get_or_create_session(request.session_id)
    pipeline = session['pipeline']
    
    if not pipeline['youtube_transcriber']:
        raise HTTPException(status_code=400, detail="YouTube transcription not configured")
    
    try:
        chunks = pipeline['youtube_transcriber'].transcribe_youtube_video(str(request.url))
        
        if chunks:
            embedded = pipeline['embedding_generator'].generate_embeddings(chunks)
            
            if not session['sources']:
                pipeline['vector_db'].create_index()
            
            pipeline['vector_db'].insert_embeddings(embedded)
            
            session['sources'].append({
                'name': f"YouTube: {request.url}",
                'type': 'youtube',
                'size': 'N/A',
                'chunks': len(chunks),
                'uploaded_at': str(uuid.uuid4())
            })
            
            return {
                "success": True,
                "url": str(request.url),
                "chunks_created": len(chunks)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/query")
async def query_documents(request: QueryRequest):
    """Query documents with RAG"""
    session = get_or_create_session(request.session_id)
    pipeline = session['pipeline']
    
    if not session['sources']:
        raise HTTPException(status_code=400, detail="No sources available. Upload documents first.")
    
    try:
        result = pipeline['rag_generator'].generate_response(
            query=request.query,
            max_chunks=request.max_chunks
        )
        
        # Save to memory if available
        if pipeline['memory']:
            pipeline['memory'].save_conversation_turn(result)
        
        # Add to chat history
        session['chat_history'].append({
            'role': 'user',
            'content': request.query
        })
        session['chat_history'].append({
            'role': 'assistant',
            'content': result.response,
            'sources': result.sources_used
        })
        
        return {
            "query": result.query,
            "response": result.response,
            "sources": result.sources_used,
            "retrieval_count": result.retrieval_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    session = get_or_create_session(session_id)
    return ChatHistoryResponse(
        messages=session['chat_history'],
        session_id=session_id
    )

@app.post("/podcast/generate")
async def generate_podcast(request: PodcastRequest):
    """Generate podcast script from sources"""
    session = get_or_create_session(request.session_id)
    pipeline = session['pipeline']
    
    if not pipeline['podcast_script_generator']:
        raise HTTPException(status_code=400, detail="Podcast generation not configured")
    
    if not session['sources']:
        raise HTTPException(status_code=400, detail="No sources available")
    
    try:
        # Get all document content
        summary_result = pipeline['rag_generator'].generate_summary(
            max_chunks=15,
            summary_length="long"
        )
        
        script = pipeline['podcast_script_generator'].generate_script_from_text(
            text_content=summary_result.response,
            source_name=request.source_name or "Knowledge Base",
            podcast_style=request.style,
            target_duration=request.duration
        )
        
        return {
            "success": True,
            "script": script.script,
            "total_lines": script.total_lines,
            "estimated_duration": script.estimated_duration,
            "source_document": script.source_document
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/podcast/synthesize")
async def synthesize_podcast(
    session_id: str,
    script_data: Dict[str, Any]
):
    """Synthesize podcast audio from script"""
    session = get_or_create_session(session_id)
    pipeline = session['pipeline']
    
    if not pipeline['podcast_tts_generator']:
        raise HTTPException(status_code=400, detail="TTS not available")
    
    try:
        from src.podcast.script_generator import PodcastScript
        
        script = PodcastScript(
            script=script_data['script'],
            source_document=script_data.get('source_document', 'Generated'),
            total_lines=len(script_data['script']),
            estimated_duration=script_data.get('estimated_duration', '10 minutes')
        )
        
        output_dir = f"./outputs/podcast_{session_id[:8]}"
        audio_files = pipeline['podcast_tts_generator'].generate_podcast_audio(
            script,
            output_dir=output_dir,
            combine_audio=True
        )
        
        # Return the combined audio file
        combined_file = [f for f in audio_files if 'complete' in f][0]
        
        return FileResponse(
            combined_file,
            media_type="audio/wav",
            filename="podcast.wav"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and cleanup resources"""
    if session_id in sessions:
        session = sessions[session_id]
        
        # Cleanup vector DB
        try:
            session['pipeline']['vector_db'].delete_collection()
            session['pipeline']['vector_db'].close()
        except:
            pass
        
        # Remove session
        del sessions[session_id]
        
        return {"success": True, "message": "Session deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_sessions": len(sessions)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
