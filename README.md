## ThinkbookLM

An open-source implementation of a document-grounded AI assistant that provides cited, verifiable answers from your personal knowledge base. Built with modern RAG architecture, vector search, and conversational memory.

### Overview 

ThinkbookLM is an intelligent document assistant that allows you to: 
- Upload and process multiple document formats (PDF, TXT, Markdown, Audio, YouTube, videos, WebPages)
- Ask questions and recieve answers backed by accurate source citations. 
- Maintain intelligent conversational context across sesions.
- Generate AI-powered podcast discussions from your documents. 
- Access a clean, intuitive web interface for seamless interaction. 

### Key Features 

- **Citation-First Responses: ** Every answer includes specific source references with page numbers and document metadata, ensuring full traceability of information.
- **Intelligent Memory Layer: **  Leverages temporal knowledge graphs to maintain conversation context, user preferences, and document relationships across sessions.
- *Multi-Format Document Support: *Seamlessly process PDFs, text files, audio recordings, YouTube videos, and web content through specialized extractors.
- *Efficient Vector Search: *Utilizes Milvus vector database with optimized indexing for fast semantic retrieval of relevant content chunks.
- *AI Podcast Generation: *Transform your documents into engaging multi-speaker audio conversations with script generation and text-to-speech synthesis.


### Technology Stack 

- *Document Processing: *PyMuPDF for PDF parsing with support for TXT and Markdown formats
- *Audio Transcription: *AssemblyAI with speaker diarization for audio files and YouTube videos
- *Web Scraping: *Firecrawl for intelligent content extraction from websites
- *Vector Database: * Milvus Lite for efficient embedding storage and similarity search
- *Memory Management: *Zep's temporal knowledge graphs for conversational context
- *Text-to-Speech: * Kokoro open-source TTS engine for podcast audio generation
- *Web Interface: * Streamlit for interactive document management and chat. 
- *Embeddings: *FastEmbed with BAAI/bge-small-en-v1.5 model for vector generation
- *Language Model: *OpenAI GPT-4 for response generation with citation report 

### Architecture 

![ThinkbookLM Architecture](assets/architecture-diagram.svg)

### System Workflow 

The system follows a comprehensive pipeline from document ingestion to response generation:
1. *Document Ingestion: *Users upload documents through the web interface or provide URLs for web content and YouTube videos.
2. *Content Processing: *Specialized processors extract text from different formats - PyMuPDF handles PDFs, AssemblyAI transcribes audio with speaker diarization, and Firecrawl scrapes web content.
3. *Text Chunking: *Content is segmented into overlapping chunks (default 1000 characters with 200 character overlap) to maintain context while enabling precise citations. 
4. *Embedding Generation: *FastEmbed converts text chunks into 384-dimensional vectors using the BAAI/bge-small-en-v1.5 model.
5. *Vector Storage: *Embeddings are indexed in Milvus using IVF (Inverted File) indexing for efficient similarity search, with metadata stored for citation purposes.
6. *Query Processing: *User queries are embedded using the same model and used to perform semantic search against the vector database.
7. *Context Retrieval: *Top-K most relevant chunks are retrieved along with their complete metadata including source file, page numbers, and timestamps.
8. *Response Generation: *The RAG generator creates responses using GPT-4, ensuring every factual claim is backed by citation references from the retrieved context.
9. *Memory Management: *Zep stores conversation history, user preferences, and document usage patterns in temporal knowledge graphs for context-aware follow-up responses.
10. *Optional Podcast Generation: *Users can transform documents into audio podcasts through script generation and multi-speaker TTS synthesis.

### Installation 

#### Prerequisites 
- Python 3.11 or 3.12
- API keys for OpenAI, AssemblyAI, Firecrawl and Zep 

#### Setup Instructions 

1. Install UV Package Manager 

```bash 
# MacOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

```

2. Create project environement: 

```bash
# Clone the project 
https://github.com/sameerdev7/Thinkbook-LM.git

# Enter the directory
cd thinkbook-lm

# Initialize virtual environment
uv venv
source .venv/bin/activate  # MacOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
uv sync

# Install additional tools
uv add -U yt-dlp
uv pip install pip
```
```

3. Configure environment variables 

Create a .env file in the project root: 


```bash
OPENAI_API_KEY=your_openai_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
FIRECRAWL_API_KEY=your_firecrawl_key
ZEP_API_KEY=your_zep_key
```

### Usage 

#### Starting the Application 

```bash 
streamlit run app.py
```

The application will launch at `http://localhost:8501`

### Using ThinkbookLM

**Library Tab**: Upload documents by dragging files or clicking the browse button. Supported formats include PDF, TXT, MD, MP3, WAV, and M4A. You can also add web pages via URL or transcribe YouTube videos.

**Research Tab**: Ask questions about your documents in the chat interface. Responses include interactive citation numbers that display source context on hover.

**Studio Tab**: Generate AI podcasts from your documents. Select source material, choose a conversational style, and set the desired length.

## Project Structure
```
thinkbook-lm/
├── src/
│   ├── audio_processing/
│   │   ├── audio_transcriber.py      # AssemblyAI transcription
│   │   └── youtube_transcriber.py    # YouTube video processing
│   ├── document_processing/
│   │   └── doc_processor.py          # PDF, TXT, MD parsing
│   ├── embeddings/
│   │   └── embedding_generator.py    # Vector generation
│   ├── generation/
│   │   └── rag.py                    # RAG pipeline
│   ├── memory/
│   │   └── memory_layer.py           # Zep integration
│   ├── podcast/
│   │   ├── script_generator.py       # Dialogue creation
│   │   └── text_to_speech.py         # Audio synthesis
│   ├── vector_database/
│   │   └── milvus_vector_db.py       # Vector storage
│   └── web_scraping/
│       └── web_scraper.py            # Web content extraction
├── data/                              # Sample documents
├── outputs/                           # Generated content
├── tests/                             # Test suites
├── app.py                             # Main application
├── pyproject.toml                     # Dependencies
└── .env.example                       # Configuration template
```

### Core Components 

#### Document Processing 

The document processor handles multiple input formats with specialized extractors. PDF files are parsed using PyMuPDF with page-level metadata extraction. Text files support UTF-8 encoding with automatic format detection. Audio files are transcribed with speaker diarization using AssemblyAI's API. YouTube videos are downloaded and transcribed with timestamp preservation. Web pages are scraped using Firecrawl with markdown conversion for clean text extraction.

#### Vector Database 

Milvus Lite provides embedded vector storage without external dependencies. The system uses IVF indexing for sub-linear search performance on large document collections. Each vector entry includes comprehensive metadata for accurate citations including source file names, page numbers, character positions, timestamps for audio, and speaker information where applicable.

#### RAG Generation 

The retrieval-augmented generation pipeline embeds user queries using the same model as documents for semantic compatibility. Top-K similarity search retrieves the most relevant chunks with their metadata intact. Context formatting includes citation markers for each chunk. The language model generates responses with inline citations, ensuring traceability. Post-processing validates that all factual claims reference appropriate sources.

#### Memory Layer 

Zep maintains conversational context through temporal knowledge graphs that capture message history, user preferences, document relationships, and query patterns. The system supports session management with automatic context retrieval, preference persistence across sessions, and semantic search over conversation history.

#### Podcast Generation 

The podcast studio transforms documents into audio content through a two-stage process. First, GPT-4 generates conversational scripts between two speakers with natural dialogue flow and topic coverage. Second, Kokoro TTS synthesizes audio with distinct male and female voices, appropriate pacing, and automatic segment combination with pauses. 


```
```
```
```
```
```
```
