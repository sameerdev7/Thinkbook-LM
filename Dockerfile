# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv pip install --system --no-cache \
    assemblyai>=0.44.3 \
    crewai>=0.193.2 \
    crewai-tools>=0.73.1 \
    fastembed>=0.7.3 \
    firecrawl-py>=4.3.6 \
    kokoro>=0.9.4 \
    pymilvus[milvus-lite]>=2.6.2 \
    pymupdf>=1.26.4 \
    python-dotenv>=1.1.1 \
    soundfile>=0.12.1 \
    streamlit>=1.28.0 \
    torch>=2.0.0 \
    torchvision>=0.15.0 \
    transformers>=4.30.0 \
    yt-dlp>=2024.12.13 \
    zep-cloud>=3.4.3 \
    zep-crewai>=1.1.1

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p outputs/podcast_audio data

# Expose Streamlit port
EXPOSE 7860

# Set environment variables
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Health check
HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
