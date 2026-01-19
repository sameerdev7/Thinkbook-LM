
# ThinkbookLM

**An open-source implementation of a document-grounded AI assistant that provides cited, verifiable answers from your personal knowledge base.**
Built with **modern RAG architecture**, **vector search**, and **conversational memory**.

---

## Overview

ThinkbookLM is an intelligent document assistant that allows you to:

- **Upload and process multiple document formats** (PDF, TXT, Markdown, Audio, YouTube, Videos, WebPages)
- **Ask questions and receive answers backed by accurate source citations**
- **Maintain intelligent conversational context across sessions**
- **Generate AI-powered podcast discussions from your documents**
- **Access a clean, intuitive web interface for seamless interaction**

---

## Key Features

- **Citation-First Responses**  
  Every answer includes **specific source references with page numbers and document metadata**, ensuring full traceability of information.

- **Intelligent Memory Layer**  
  Leverages **temporal knowledge graphs** to maintain conversation context, user preferences, and document relationships across sessions.

- **Multi-Format Document Support**  
  Seamlessly process PDFs, text files, audio recordings, YouTube videos, and web content through specialized extractors.

- **Efficient Vector Search**  
  Utilizes **Milvus vector database** with optimized indexing for fast semantic retrieval of relevant content chunks.

- **AI Podcast Generation**  
  Transform documents into **multi-speaker audio conversations** with script generation and text-to-speech synthesis.

---

## Technology Stack

- **Document Processing:** PyMuPDF for PDF parsing with support for TXT and Markdown formats  
- **Audio Transcription:** AssemblyAI with speaker diarization for audio files and YouTube videos  
- **Web Scraping:** Firecrawl for intelligent content extraction from websites  
- **Vector Database:** Milvus Lite for efficient embedding storage and similarity search  
- **Memory Management:** Zep temporal knowledge graphs for conversational context  
- **Text-to-Speech:** Kokoro open-source TTS engine for podcast audio generation  
- **Web Interface:** Streamlit for interactive document management and chat  
- **Embeddings:** FastEmbed with BAAI/bge-small-en-v1.5  
- **Language Model:** OpenAI GPT-4 with citation reports

---

## Architecture

![ThinkbookLM Architecture](assets/architecture-diagram.svg)

---

## System Workflow

1. **Document Ingestion**  
   Users upload documents via the web interface or provide URLs for web content and YouTube videos.

2. **Content Processing**  
   Specialized processors extract text from different formats:
   - PDFs: PyMuPDF  
   - Audio: AssemblyAI (with speaker diarization)  
   - Web: Firecrawl

3. **Text Chunking**  
   Content is segmented into **overlapping chunks** (default: 1000 characters with 200 overlap) to preserve context and enable precise citations.

4. **Embedding Generation**  
   FastEmbed converts chunks into **384-dimensional vectors** using BAAI/bge-small-en-v1.5.

5. **Vector Storage**  
   Embeddings are indexed in Milvus using **IVF indexing**, with metadata stored for citation.

6. **Query Processing**  
   User queries are embedded using the same model and matched via semantic search.

7. **Context Retrieval**  
   Top-K relevant chunks are retrieved with full metadata (file, page numbers, timestamps).

8. **Response Generation**  
   GPT-4 generates answers where **every factual claim is citation-backed**.

9. **Memory Management**  
   Zep stores conversation history, preferences, and document usage patterns.

10. **Optional Podcast Generation**  
    Documents can be converted into audio podcasts using scripted multi-speaker TTS.

---

## Installation

### Prerequisites

- **Python 3.11 or 3.12**
- API keys for **OpenAI**, **AssemblyAI**, **Firecrawl**, and **Zep**

### Setup Instructions

```bash
# Clone the repository
https://github.com/sameerdev7/Thinkbook-LM.git

# Enter directory
cd thinkbook-lm

# Create virtual environment
uv venv
source .venv/bin/activate    # MacOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
uv sync

# Additional tools
uv add -U yt-dlp
uv pip install pip
```

### Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_key
ASSEMBLYAI_API_KEY=your_assemblyai_key
FIRECRAWL_API_KEY=your_firecrawl_key
ZEP_API_KEY=your_zep_key
```

---

## Usage

### Start the Application

```bash
streamlit run app.py
```

Application runs at: `http://localhost:8501`

---

## Interface Guide

- **Library Tab:** Upload documents or URLs (PDF, TXT, MD, MP3, WAV, M4A, YouTube)
- **Research Tab:** Ask questions and receive answers with interactive citations
- **Studio Tab:** Generate AI podcasts with selectable style and length

---

## Project Structure

```text
thinkbook-lm/
├── src/
│   ├── audio_processing/
│   ├── document_processing/
│   ├── embeddings/
│   ├── generation/
│   ├── memory/
│   ├── podcast/
│   ├── vector_database/
│   └── web_scraping/
├── data/
├── outputs/
├── tests/
├── app.py
├── pyproject.toml
└── .env.example
```

---

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
