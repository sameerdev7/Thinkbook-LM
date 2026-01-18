import streamlit as st
import os
import tempfile
import time
import logging
from typing import List, Dict, Any
import uuid
from pathlib import Path
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- API KEY CHECKING ---
def check_api_keys():
    """Check which API keys are configured"""
    keys_status = {
        'OPENAI_API_KEY': bool(os.getenv("OPENAI_API_KEY")),
        'ASSEMBLYAI_API_KEY': bool(os.getenv("ASSEMBLYAI_API_KEY")),
        'FIRECRAWL_API_KEY': bool(os.getenv("FIRECRAWL_API_KEY")),
        'ZEP_API_KEY': bool(os.getenv("ZEP_API_KEY"))
    }
    return keys_status

def show_setup_screen():
    """Display setup instructions when API keys are missing"""
    st.markdown("""
    <style>
        .setup-container {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 2px solid #6366f1;
            border-radius: 20px;
            padding: 3rem;
            margin: 2rem 0;
            text-align: center;
        }
        .setup-title {
            background: linear-gradient(135deg, #a78bfa 0%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 1rem;
        }
        .setup-subtitle {
            color: #94a3b8;
            font-size: 1.2rem;
            margin-bottom: 2rem;
        }
        .key-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            text-align: left;
        }
        .key-required {
            color: #ef4444;
            font-weight: 600;
        }
        .key-optional {
            color: #eab308;
            font-weight: 600;
        }
        .key-configured {
            color: #10b981;
            font-weight: 600;
        }
        .setup-code {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 1rem;
            font-family: monospace;
            color: #e2e8f0;
            margin: 1rem 0;
            text-align: left;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="setup-container">
        <h1 class="setup-title">⚙️ Setup Required</h1>
        <p class="setup-subtitle">Configure your API keys to unlock ThinkbookLM's full potential</p>
    </div>
    """, unsafe_allow_html=True)
    
    keys_status = check_api_keys()
    
    # OpenAI Key (Required)
    status_class = "key-configured" if keys_status['OPENAI_API_KEY'] else "key-required"
    status_text = "✅ Configured" if keys_status['OPENAI_API_KEY'] else "❌ Required"
    st.markdown(f"""
    <div class="key-card">
        <h3>OpenAI API Key <span class="{status_class}">{status_text}</span></h3>
        <p>Required for: Embeddings, RAG responses, and podcast script generation</p>
        <p>Get your key at: <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI API Keys</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    # AssemblyAI Key (Optional)
    status_class = "key-configured" if keys_status['ASSEMBLYAI_API_KEY'] else "key-optional"
    status_text = "✅ Configured" if keys_status['ASSEMBLYAI_API_KEY'] else "⚠️ Optional"
    st.markdown(f"""
    <div class="key-card">
        <h3>AssemblyAI API Key <span class="{status_class}">{status_text}</span></h3>
        <p>Required for: Audio transcription and YouTube video processing</p>
        <p>Get your key at: <a href="https://www.assemblyai.com/dashboard/signup" target="_blank">AssemblyAI</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Firecrawl Key (Optional)
    status_class = "key-configured" if keys_status['FIRECRAWL_API_KEY'] else "key-optional"
    status_text = "✅ Configured" if keys_status['FIRECRAWL_API_KEY'] else "⚠️ Optional"
    st.markdown(f"""
    <div class="key-card">
        <h3>Firecrawl API Key <span class="{status_class}">{status_text}</span></h3>
        <p>Required for: Web scraping functionality</p>
        <p>Get your key at: <a href="https://www.firecrawl.dev" target="_blank">Firecrawl</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Zep Key (Optional)
    status_class = "key-configured" if keys_status['ZEP_API_KEY'] else "key-optional"
    status_text = "✅ Configured" if keys_status['ZEP_API_KEY'] else "⚠️ Optional"
    st.markdown(f"""
    <div class="key-card">
        <h3>Zep Cloud API Key <span class="{status_class}">{status_text}</span></h3>
        <p>Required for: Conversation memory across sessions</p>
        <p>Get your key at: <a href="https://www.getzep.com" target="_blank">Zep Cloud</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🚀 How to Configure on Hugging Face Spaces")
    st.markdown("""
    <div class="setup-code">
    1. Go to your Space Settings<br>
    2. Navigate to "Variables and secrets"<br>
    3. Add each API key as a new secret:<br>
       • Name: OPENAI_API_KEY<br>
       • Value: your-api-key-here<br>
    4. Save and restart the Space
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔧 How to Configure Locally")
    st.markdown("""
    <div class="setup-code">
    # Create a .env file in the project root:<br>
    OPENAI_API_KEY=your-key-here<br>
    ASSEMBLYAI_API_KEY=your-key-here<br>
    FIRECRAWL_API_KEY=your-key-here<br>
    ZEP_API_KEY=your-key-here<br>
    <br>
    # Then restart the application
    </div>
    """, unsafe_allow_html=True)
    
    # Show demo mode option
    st.markdown("---")
    st.info("💡 **Demo Mode**: You can explore the UI without API keys, but features requiring external services will be disabled.")
    
    if st.button("🎬 Continue in Demo Mode", type="primary"):
        st.session_state.demo_mode = True
        st.rerun()

# --- STYLING & BRANDING ---
def apply_custom_design():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* Global Reset */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #f1f5f9;
        }

        /* ThinkbookLM Branding */
        .brand-container {
            text-align: center;
            padding: 2rem 0;
        }
        
        .brand-title {
            background: linear-gradient(135deg, #a78bfa 0%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin: 0;
        }
        
        .brand-subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
            font-weight: 400;
            margin-top: 0.5rem;
        }

        /* Sidebar & Source Items */
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid #1e293b;
        }
        
        .sidebar-header {
            font-size: 1.2rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #1e293b;
        }

        .source-item {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 12px;
            margin: 8px 0;
            transition: all 0.2s ease;
        }
        
        .source-item:hover {
            border-color: #6366f1;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .source-title {
            font-weight: 600;
            color: #f8fafc;
            font-size: 0.9rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .source-meta {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 4px;
        }

        /* Chat Messages */
        .chat-message {
            border-radius: 16px;
            padding: 20px;
            margin: 16px 0;
            line-height: 1.6;
            border: 1px solid transparent;
        }
        
        .user-message {
            background: #1e293b;
            border-color: #334155;
            margin-left: 10%;
            color: #f1f5f9;
        }
        
        .assistant-message {
            background: #0f172a;
            border-color: #6366f1;
            margin-right: 10%;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        /* Interactive Citations */
        .citation-number {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            border: 1px solid rgba(99, 102, 241, 0.3);
            cursor: help;
            display: inline-block;
            position: relative;
        }
        
        .citation-tooltip {
            position: absolute;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            color: #e2e8f0;
            padding: 14px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            border: 1px solid #475569;
            width: 320px;
            z-index: 1000;
            font-size: 0.85rem;
            opacity: 0;
            visibility: hidden;
            transition: all 0.2s ease;
            pointer-events: none;
        }
        
        .citation-number:hover .citation-tooltip {
            opacity: 1;
            visibility: visible;
        }

        /* Components */
        .stButton > button {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: opacity 0.2s !important;
        }
        
        .stButton > button:hover {
            opacity: 0.9 !important;
        }
        
        .upload-area {
            border: 2px dashed #334155;
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            background: rgba(30, 41, 59, 0.5);
            margin: 20px 0;
        }

        .studio-card {
            background: #1e293b;
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid #334155;
        }
        
        .demo-badge {
            background: rgba(234, 179, 8, 0.1);
            border: 1px solid #eab308;
            color: #eab308;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }
    </style>
    """, unsafe_allow_html=True)

# --- PIPELINE IMPORTS (with error handling) ---
try:
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
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Import error: {e}. Ensure src/ directory is in path.")
    IMPORTS_AVAILABLE = False

# --- UTILITY FUNCTIONS ---
def create_interactive_citations(response_text: str, sources_used: List[Dict[str, Any]]) -> str:
    citation_map = {}
    for source in sources_used:
        ref = source.get('reference', '')
        if ref:
            match = re.search(r'\[(\d+)\]', ref)
            if match:
                num = match.group(1)
                citation_map[num] = source
    
    def replace_citation(match):
        num = match.group(1)
        if num in citation_map:
            source = citation_map[num]
            chunk_content = "Content not available"
            source_info = f"Source: {source.get('source_file', 'Unknown')}"
            
            if source.get('page_number'):
                source_info += f", Page: {source['page_number']}"
            
            try:
                if st.session_state.pipeline and st.session_state.pipeline['vector_db']:
                    chunk_id = source.get('chunk_id')
                    if chunk_id:
                        chunk_data = st.session_state.pipeline['vector_db'].get_chunk_by_id(chunk_id)
                        if chunk_data and chunk_data.get('content'):
                            chunk_content = chunk_data['content'][:300] + "..."
            except Exception:
                chunk_content = "Preview unavailable"
            
            c_esc = chunk_content.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            s_esc = source_info.replace('"', '&quot;')
            
            return f'''<span class="citation-number">
                {num}
                <div class="citation-tooltip">
                    <div style="font-weight:bold; color:#818cf8; margin-bottom:4px;">{s_esc}</div>
                    <div>{c_esc}</div>
                </div>
            </span>'''
        return match.group(0)

    return re.sub(r'\[(\d+)\]', replace_citation, response_text)

def init_session_state():
    if 'pipeline' not in st.session_state: st.session_state.pipeline = None
    if 'sources' not in st.session_state: st.session_state.sources = []
    if 'chat_history' not in st.session_state: st.session_state.chat_history = []
    if 'session_id' not in st.session_state: st.session_state.session_id = str(uuid.uuid4())
    if 'pipeline_initialized' not in st.session_state: st.session_state.pipeline_initialized = False
    if 'demo_mode' not in st.session_state: st.session_state.demo_mode = False
    if 'api_keys_checked' not in st.session_state: st.session_state.api_keys_checked = False

def reset_chat():
    try:
        if st.session_state.pipeline and st.session_state.pipeline['memory']:
            st.session_state.pipeline['memory'].clear_session()
        st.session_state.chat_history = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
    except Exception as e:
        st.error(f"Error resetting: {e}")

def initialize_pipeline():
    if st.session_state.pipeline_initialized: 
        return True
    
    if not IMPORTS_AVAILABLE:
        st.error("❌ Core modules could not be imported. Check logs for details.")
        return False
    
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
        firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
        zep_key = os.getenv("ZEP_API_KEY")
        
        if not openai_key and not st.session_state.demo_mode:
            return False
        
        with st.spinner("Waking up ThinkbookLM..."):
            doc_processor = DocumentProcessor()
            embedding_generator = EmbeddingGenerator() if openai_key else None
            
            vector_db = None
            if openai_key:
                vector_db = MilvusVectorDB(
                    db_path=f"./milvus_lite_{st.session_state.session_id[:8]}.db", 
                    collection_name=f"collection_{st.session_state.session_id[:8]}"
                )
            
            rag_generator = None
            if openai_key and embedding_generator and vector_db:
                rag_generator = RAGGenerator(
                    embedding_generator=embedding_generator, 
                    vector_db=vector_db, 
                    openai_api_key=openai_key
                )
            
            audio_transcriber = AudioTranscriber(assemblyai_key) if assemblyai_key else None
            youtube_transcriber = YouTubeTranscriber(assemblyai_key) if assemblyai_key else None
            web_scraper = WebScraper(firecrawl_key) if firecrawl_key else None
            podcast_gen = PodcastScriptGenerator(openai_key) if openai_key else None
            
            tts_gen = None
            try:
                tts_gen = PodcastTTSGenerator()
            except: 
                logger.warning("TTS Engine not found.")

            memory = None
            if zep_key and openai_key:
                memory = NotebookMemoryLayer(
                    user_id="think_user", 
                    session_id=st.session_state.session_id, 
                    create_new_session=True
                )
            
            st.session_state.pipeline = {
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
            }
            st.session_state.pipeline_initialized = True
            return True
    except Exception as e:
        st.error(f"Pipeline failure: {e}")
        logger.error(f"Pipeline initialization error: {e}", exc_info=True)
        return False

# --- PROCESSING LOGIC ---
def process_uploaded_files(uploaded_files):
    pipeline = st.session_state.pipeline
    
    if not pipeline['embedding_generator'] or not pipeline['vector_db']:
        st.error("❌ Document processing requires OpenAI API key")
        return
    
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name
        
        try:
            if uploaded_file.type.startswith('audio/'):
                if not pipeline['audio_transcriber']:
                    st.warning(f"⚠️ Skipping {uploaded_file.name}: Audio transcription requires AssemblyAI API key")
                    continue
                chunks = pipeline['audio_transcriber'].transcribe_audio(temp_path)
                s_type = "Audio"
            else:
                chunks = pipeline['doc_processor'].process_document(temp_path)
                s_type = "Document"
            
            for c in chunks: c.source_file = uploaded_file.name
            
            if chunks:
                embedded = pipeline['embedding_generator'].generate_embeddings(chunks)
                if not st.session_state.sources: pipeline['vector_db'].create_index()
                pipeline['vector_db'].insert_embeddings(embedded)
                st.session_state.sources.append({
                    'name': uploaded_file.name, 'type': s_type, 
                    'size': f"{len(uploaded_file.getbuffer())/1024:.1f} KB", 'chunks': len(chunks),
                    'uploaded_at': time.strftime("%H:%M")
                })
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")
        finally:
            os.unlink(temp_path)

# --- UI COMPONENTS ---
def render_sidebar():
    with st.sidebar:
        # Demo mode indicator
        if st.session_state.demo_mode:
            st.markdown('<div class="demo-badge">🎬 DEMO MODE</div>', unsafe_allow_html=True)
            st.caption("Some features disabled without API keys")
            st.markdown("---")
        
        st.markdown('<div class="sidebar-header">📚 Knowledge Base</div>', unsafe_allow_html=True)
        if st.session_state.sources:
            for source in st.session_state.sources:
                st.markdown(f'''
                <div class="source-item">
                    <div class="source-title">{source['name']}</div>
                    <div class="source-meta">{source['type']} • {source['chunks']} segments</div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("No sources added yet.")
        
        st.markdown("---")
        if st.button("🔄 Reset Session"):
            reset_chat()

def render_add_sources():
    st.markdown("### 📂 Expand your Library")
    
    if st.session_state.demo_mode:
        st.warning("⚠️ Document processing requires OpenAI API key. Please configure API keys to use this feature.")
    
    uploaded = st.file_uploader(
        "Upload Documents or Audio", 
        accept_multiple_files=True, 
        type=['pdf','txt','mp3','wav','md'],
        disabled=st.session_state.demo_mode
    )
    
    if uploaded and st.button("Process Assets", disabled=st.session_state.demo_mode):
        process_uploaded_files(uploaded)
        st.rerun()
    
    t1, t2 = st.tabs(["🌐 Web", "🎥 Video"])
    with t1:
        url = st.text_input("Website URL", disabled=st.session_state.demo_mode)
        if st.button("Scrape Site", disabled=st.session_state.demo_mode) and url:
            if not st.session_state.pipeline['web_scraper']:
                st.error("❌ Web scraping requires Firecrawl API key")
            else:
                st.info("Scraping started...") 
    with t2:
        yt = st.text_input("YouTube URL", disabled=st.session_state.demo_mode)
        if st.button("Transcribe Video", disabled=st.session_state.demo_mode) and yt:
            if not st.session_state.pipeline['youtube_transcriber']:
                st.error("❌ YouTube transcription requires AssemblyAI API key")
            else:
                st.info("Downloading transcript...")

def render_chat():
    st.markdown("### 💬 Research Insights")
    
    if st.session_state.demo_mode:
        st.info("💡 Chat functionality requires OpenAI API key. Configure API keys to start chatting with your documents.")
    
    for msg in st.session_state.chat_history:
        div_class = "user-message" if msg['role'] == 'user' else "assistant-message"
        content = msg.get('interactive_content', msg['content'])
        st.markdown(f'<div class="chat-message {div_class}">{content}</div>', unsafe_allow_html=True)

    query = st.chat_input("Analyze your sources...", disabled=st.session_state.demo_mode)
    if query:
        if not st.session_state.pipeline['rag_generator']:
            st.error("❌ Chat requires OpenAI API key")
            return
        
        st.session_state.chat_history.append({'role': 'user', 'content': query})
        with st.spinner("Synthesizing..."):
            try:
                result = st.session_state.pipeline['rag_generator'].generate_response(query)
                interactive = create_interactive_citations(result.response, result.sources_used)
                st.session_state.chat_history.append({
                    'role': 'assistant', 'content': result.response, 'interactive_content': interactive
                })
            except Exception as e:
                st.error(f"Error generating response: {e}")
        st.rerun()

def render_studio():
    st.markdown("### 🎙️ Creative Studio")
    
    if st.session_state.demo_mode:
        st.warning("⚠️ Podcast generation requires OpenAI API key. Configure API keys to use this feature.")
    
    if not st.session_state.sources:
        st.warning("Add sources to unlock the Studio.")
        return
    
    st.markdown("""
    <div class="studio-card">
        <h4>Podcast Generation</h4>
        <p style="color:#94a3b8">Transform notes into a synthesized conversation between two AI experts.</p>
    </div>
    """, unsafe_allow_html=True)
    
    src_list = [s['name'] for s in st.session_state.sources]
    selected = st.selectbox("Source Material", src_list, disabled=st.session_state.demo_mode)
    col1, col2 = st.columns(2)
    with col1: style = st.selectbox("Style", ["Deep Dive", "Quick Summary", "Narrative"], disabled=st.session_state.demo_mode)
    with col2: length = st.selectbox("Length", ["5 min", "15 min"], disabled=st.session_state.demo_mode)
    
    if st.button("Generate Audio Episode", disabled=st.session_state.demo_mode):
        if not st.session_state.pipeline['podcast_script_generator']:
            st.error("❌ Podcast generation requires OpenAI API key")
        else:
            st.success("Drafting script and synthesizing voice...")

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="ThinkbookLM", page_icon="🧠", layout="wide")
    apply_custom_design()
    init_session_state()
    
    # Check API keys on first load
    if not st.session_state.api_keys_checked:
        keys_status = check_api_keys()
        if not keys_status['OPENAI_API_KEY'] and not st.session_state.demo_mode:
            show_setup_screen()
            st.session_state.api_keys_checked = True
            return
        st.session_state.api_keys_checked = True
    
    # Initialize pipeline
    if not initialize_pipeline(): 
        if not st.session_state.demo_mode:
            show_setup_screen()
            return

    # Main app header
    st.markdown("""
    <div class="brand-container">
        <h1 class="brand-title">ThinkbookLM</h1>
        <p class="brand-subtitle">The Intelligence Layer for Your Personal Knowledge Base</p>
    </div>
    """, unsafe_allow_html=True)

    render_sidebar()

    tab_library, tab_chat, tab_studio = st.tabs(["📂 Library", "💬 Research", "🎨 Studio"])
    
    with tab_library: render_add_sources()
    with tab_chat: render_chat()
    with tab_studio: render_studio()

if __name__ == "__main__":
    main()
