#!/bin/bash

# ThinkbookLM Deployment Script
# This script helps you test locally and deploy to Hugging Face

set -e

echo "🧠 ThinkbookLM Deployment Helper"
echo "================================"
echo ""

# Function to check if command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command_exists docker; then
  echo "❌ Docker is not installed. Please install Docker first."
  exit 1
fi

if ! command_exists git; then
  echo "❌ Git is not installed. Please install Git first."
  exit 1
fi

echo "✅ Prerequisites satisfied"
echo ""

# Main menu
echo "What would you like to do?"
echo "1) Build Docker image locally"
echo "2) Test locally with Docker"
echo "3) Test locally with docker-compose"
echo "4) Deploy to Hugging Face"
echo "5) Exit"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
1)
  echo ""
  echo "🔨 Building Docker image..."
  docker build -t thinkbooklm:latest .
  echo "✅ Image built successfully!"
  echo ""
  echo "To run it: docker run -p 7860:7860 -e OPENAI_API_KEY=your_key thinkbooklm:latest"
  ;;

2)
  echo ""
  read -p "Enter your OPENAI_API_KEY: " openai_key
  echo ""
  echo "🚀 Starting ThinkbookLM..."
  docker run -p 7860:7860 \
    -e OPENAI_API_KEY="$openai_key" \
    -e ASSEMBLYAI_API_KEY="${ASSEMBLYAI_API_KEY:-}" \
    -e FIRECRAWL_API_KEY="${FIRECRAWL_API_KEY:-}" \
    -e ZEP_API_KEY="${ZEP_API_KEY:-}" \
    thinkbooklm:latest
  ;;

3)
  echo ""
  if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating template..."
    cat >.env <<EOF
OPENAI_API_KEY=your_openai_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_key_here
FIRECRAWL_API_KEY=your_firecrawl_key_here
ZEP_API_KEY=your_zep_key_here
EOF
    echo "✅ Created .env file. Please edit it with your API keys."
    echo ""
    read -p "Press Enter after updating .env file..."
  fi

  echo "🚀 Starting with docker-compose..."
  docker compose up --build
  ;;

4)
  echo ""
  echo "🚀 Deploying to Hugging Face Spaces"
  echo "===================================="
  echo ""
  echo "Prerequisites:"
  echo "1. Create a new Space at https://huggingface.co/new-space"
  echo "2. Choose 'Docker' as the SDK"
  echo "3. Clone the Space repository locally"
  echo ""
  read -p "Have you created a Space? (y/n): " created

  if [ "$created" != "y" ]; then
    echo "Please create a Space first, then run this script again."
    exit 0
  fi

  read -p "Enter your Hugging Face username: " hf_user
  read -p "Enter your Space name: " space_name

  echo ""
  echo "📦 Preparing deployment..."

  # Create temporary directory
  temp_dir=$(mktemp -d)
  echo "Created temp directory: $temp_dir"

  # Clone the Space
  echo "Cloning Space repository..."
  git clone "https://huggingface.co/spaces/$hf_user/$space_name" "$temp_dir"

  # Copy files
  echo "Copying application files..."
  cp -r src "$temp_dir/"
  cp app.py "$temp_dir/"
  cp Dockerfile "$temp_dir/"
  cp .dockerignore "$temp_dir/"
  cp pyproject.toml "$temp_dir/"

  # Create README with proper frontmatter
  cat >"$temp_dir/README.md" <<'EOF'
---
title: ThinkbookLM
emoji: 🧠
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# ThinkbookLM 🧠

The Intelligence Layer for Your Personal Knowledge Base

See full documentation in the application.
EOF

  # Git operations
  cd "$temp_dir"
  git add .
  git commit -m "Deploy ThinkbookLM application"

  echo ""
  echo "📤 Pushing to Hugging Face..."
  git push

  echo ""
  echo "✅ Deployment complete!"
  echo ""
  echo "🔑 Don't forget to set your secrets in Space settings:"
  echo "   - OPENAI_API_KEY (Required)"
  echo "   - ASSEMBLYAI_API_KEY (Optional)"
  echo "   - FIRECRAWL_API_KEY (Optional)"
  echo "   - ZEP_API_KEY (Optional)"
  echo ""
  echo "Your Space will be available at:"
  echo "https://huggingface.co/spaces/$hf_user/$space_name"

  # Cleanup
  rm -rf "$temp_dir"
  ;;

5)
  echo "Goodbye! 👋"
  exit 0
  ;;

*)
  echo "Invalid choice. Please run the script again."
  exit 1
  ;;
esac
