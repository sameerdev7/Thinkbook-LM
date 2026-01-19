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

# --- API KEY MANAGEMENT ---
def get_api_keys():
    """Get API keys from either environment or user input"""
    # Try environment first (for Space owner's keys)
    env_keys = {
        'OPENAI_API_KEY': os.getenv("OPENAI_API_KEY"),
        'ASSEMBLYAI_API_KEY': os.getenv("ASSEMBLYAI_API_KEY"),
        'FIRECRAWL_API_KEY': os.getenv("FIRECRAWL_API_KEY"),
        'ZEP_API_KEY': os.getenv("ZEP_API_KEY")
    }
    
    # If user provided keys in session, use those instead
    if 'user_api_keys' in st.session_state:
        for key, value in st.session_state.user_api_keys.items():
            if value:  # User-provided keys override environment
                env_keys[key] = value
    
    return env_keys

def show_api_key_input_sidebar():
    """Show API key input in sidebar for users who want to use their own keys"""
    with st.sidebar:
        st.markdown("---")
        with st.expander("🔑 Use Your Own API Keys", expanded=False):
            st.markdown("""
            <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 1rem;">
                Enter your own API keys to use ThinkbookLM without relying on shared resources.
                Your keys are stored only in your browser session and never saved.
            </div>
            """, unsafe_allow_html=True)
            
            if 'user_api_keys' not in st.session_state:
                st.session_state.user_api_keys = {
                    'OPENAI_API_KEY': '',
                    'ASSEMBLYAI_API_KEY': '',
                    'FIRECRAWL_API_KEY': '',
                    'ZEP_API_KEY': ''
                }
            
            # OpenAI Key
            openai_key = st.text_input(
                "OpenAI API Key (Required)",
                type="password",
                value=st.session_state.user_api_keys['OPENAI_API_KEY'],
                help="Get your key at https://platform.openai.com/api-keys"
            )
            st.session_state.user_api_keys['OPENAI_API_KEY'] = openai_key
            
            # AssemblyAI Key
            assemblyai_key = st.text_input(
                "AssemblyAI Key (Optional)",
                type="password",
                value=st.session_state.user_api_keys['ASSEMBLYAI_API_KEY'],
                help="For audio transcription"
            )
            st.session_state.user_api_keys['ASSEMBLYAI_API_KEY'] = assemblyai_key
            
            # Firecrawl Key
            firecrawl_key = st.text_input(
                "Firecrawl Key (Optional)",
                type="password",
                value=st.session_state.user_api_keys['FIRECRAWL_API_KEY'],
                help="For web scraping"
            )
            st.session_state.user_api_keys['FIRECRAWL_API_KEY'] = firecrawl_key
            
            # Zep Key
            zep_key = st.text_input(
                "Zep Cloud Key (Optional)",
                type="password",
                value=st.session_state.user_api_keys['ZEP_API_KEY'],
                help="For conversation memory"
            )
            st.session_state.user_api_keys['ZEP_API_KEY'] = zep_key
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Apply Keys", use_container_width=True):
                    st.session_state.pipeline_initialized = False
                    st.rerun()
            with col2:
                if st.button("🗑️ Clear Keys", use_container_width=True):
                    st.session_state.user_api_keys = {
                        'OPENAI_API_KEY': '',
                        'ASSEMBLYAI_API_KEY': '',
                        'FIRECRAWL_API_KEY': '',
                        'ZEP_API_KEY': ''
                    }
                    st.session_state.pipeline_initialized = False
                    st.rerun()

def check_api_keys():
    """Check which API keys are configured"""
    keys = get_api_keys()
    return {k: bool(v) for k, v in keys.items()}

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
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="setup-container">
        <h1 class="setup-title">🧠 Welcome to ThinkbookLM</h1>
        <p class="setup-subtitle">Your Intelligent Knowledge Base</p>
    </div>
    """, unsafe_allow_html=True)
    
    keys_status = check_api_keys()
    
    st.markdown("### 🔐 API Keys Status")
    
    # OpenAI Key (Required)
    status_class = "key-configured" if keys_status['OPENAI_API_KEY'] else "key-required"
    status_text = "✅ Configured" if keys_status['OPENAI_API_KEY'] else "❌ Required"
    st.markdown(f"""
    <div class="key-card">
        <h3>OpenAI API Key <span class="{status_class}">{status_text}</span></h3>
        <p>Required for: Embeddings, RAG responses, and podcast generation</p>
        <p>Get your key at: <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI API Keys</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    # AssemblyAI Key (Optional)
    status_class = "key-configured" if keys_status['ASSEMBLYAI_API_KEY'] else "key-optional"
    status_text = "✅ Configured" if keys_status['ASSEMBLYAI_API_KEY'] else "⚠️ Optional"
    st.markdown(f"""
    <div class="key-card">
        <h3>AssemblyAI API Key <span class="{status_class}">{status_text}</span></h3>
        <p>Required for: Audio transcription and YouTube processing</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("💡 **Tip**: Enter your API keys in the sidebar to get started. Your keys are stored only in your browser session.")
    
    if st.button("🎬 Continue in Demo Mode", type="primary"):
        st.session_state.demo_mode = True
        st.rerun()

# --- STYLING & BRANDING ---
def apply_custom_design():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #f1f5f9;
        }

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
        }

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

# --- PIPELINE IMPORTS ---
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
    logger.error(f"Import error: {e}")
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
            return f'<span class="citation-number">[{num}]</span>'
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
    if 'user_api_keys' not in st.session_state: 
        st.session_state.user_api_keys = {
            'OPENAI_API_KEY': '',
            'ASSEMBLYAI_API_KEY': '',
            'FIRECRAWL_API_KEY': '',
            'ZEP_API_KEY': ''
        }

def initialize_pipeline():
    if st.session_state.pipeline_initialized: 
        return True
    
    if not IMPORTS_AVAILABLE:
        st.error("❌ Core modules could not be imported.")
        return False
    
    try:
        # Get API keys (from environment or user input)
        keys = get_api_keys()
        openai_key = keys['OPENAI_API_KEY']
        assemblyai_key = keys['ASSEMBLYAI_API_KEY']
        firecrawl_key = keys['FIRECRAWL_API_KEY']
        zep_key = keys['ZEP_API_KEY']
        
        if not openai_key and not st.session_state.demo_mode:
            return False
        
        with st.spinner("Initializing ThinkbookLM..."):
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
                pass

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
        return False

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
                    st.warning(f"⚠️ Skipping {uploaded_file.name}: Requires AssemblyAI key")
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
        # Show API key input option
        show_api_key_input_sidebar()
        
        # Demo mode indicator
        if st.session_state.demo_mode:
            st.markdown('<div class="demo-badge">🎬 DEMO MODE</div>', unsafe_allow_html=True)
            st.caption("Some features disabled")
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

def render_add_sources():
    st.markdown("### 📂 Expand your Library")
    
    if st.session_state.demo_mode:
        st.warning("⚠️ Document processing requires OpenAI API key.")
    
    uploaded = st.file_uploader(
        "Upload Documents or Audio", 
        accept_multiple_files=True, 
        type=['pdf','txt','mp3','wav','md'],
        disabled=st.session_state.demo_mode
    )
    
    if uploaded and st.button("Process Assets", disabled=st.session_state.demo_mode):
        process_uploaded_files(uploaded)
        st.rerun()

def render_chat():
    st.markdown("### 💬 Research Insights")
    
    if st.session_state.demo_mode:
        st.info("💡 Chat requires OpenAI API key. Add your key in the sidebar.")
    
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
                st.error(f"Error: {e}")
        st.rerun()

def render_studio():
    st.markdown("### 🎙️ Creative Studio")
    
    if st.session_state.demo_mode:
        st.warning("⚠️ Podcast generation requires OpenAI API key.")
    
    if not st.session_state.sources:
        st.warning("Add sources to unlock the Studio.")
        return
    
    st.markdown("""
    <div style="background: #1e293b; border-radius: 20px; padding: 2rem; border: 1px solid #334155;">
        <h4>Podcast Generation</h4>
        <p style="color:#94a3b8">Transform notes into AI conversations.</p>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="ThinkbookLM", page_icon="🧠", layout="wide")
    apply_custom_design()
    init_session_state()
    
    # Check API keys
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
