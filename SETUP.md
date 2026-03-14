# MedAgent — Setup Guide

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

---

## Quick Start (Docker)

```bash
# 1. Clone and enter project
cd MedAgent

# 2. Set your Anthropic API key
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and SECRET_KEY

# 3. Launch everything
docker compose up --build

# Services:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API docs:  http://localhost:8000/docs
#   MinIO UI:  http://localhost:9001  (user: medagent_minio / medagent_minio_secret)
```

---

## Local Development

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR (for image/scanned PDF support)
# macOS:  brew install tesseract poppler
# Ubuntu: apt-get install tesseract-ocr poppler-utils

# Start PostgreSQL + MinIO via Docker
docker compose up postgres minio -d

# Set env (point to localhost instead of docker hostnames)
export DATABASE_URL="postgresql+asyncpg://medagent:medagent_secret@localhost:5432/medagent_db"
export DATABASE_URL_SYNC="postgresql://medagent:medagent_secret@localhost:5432/medagent_db"
export MINIO_ENDPOINT="localhost:9000"
export ANTHROPIC_API_KEY="your-key"
export SECRET_KEY="your-secret"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # starts at http://localhost:3000
```

---

## Architecture Overview

```
Browser (React)
    │  REST + SSE
    ▼
FastAPI (Python)
    ├── Auth (JWT + refresh tokens)
    ├── Documents (upload → OCR → chunk → embed)
    ├── Chat (streaming SSE with Claude claude-sonnet-4-6)
    ├── Health Timeline
    └── Prescriptions
         │
         ▼
    PostgreSQL + pgvector
    ├── All tables with Row Level Security
    └── HNSW vector index (384-dim, all-MiniLM-L6-v2)

    MinIO (S3-compatible file storage)
    Claude claude-sonnet-4-6 (Anthropic API — LLM)
    all-MiniLM-L6-v2 (local embeddings, free)
```

---

## Zero-Leak RAG

Every vector chunk stored in pgvector has `user_id` metadata.
All similarity searches ALWAYS include `WHERE user_id = :user_id`.
PostgreSQL Row Level Security policies provide a second enforcement layer.
No user's data can ever appear in another user's RAG results.

---

## Document Processing Pipeline

```
Upload → MinIO → BackgroundTask
  1. OCR / text extraction
     - pdfplumber for digital PDFs (preserves tables)
     - pdf2image + pytesseract for scanned PDFs
     - pytesseract for images
  2. Smart chunking
     - Lab reports: line-group chunking (preserves test-value-range)
     - Other docs: RecursiveCharacterTextSplitter (512 tokens, 64 overlap)
  3. Embedding (all-MiniLM-L6-v2, runs locally)
  4. Store in pgvector with user_id metadata
```

---

## Medical Agent

- **LLM**: Claude claude-sonnet-4-6 via LangChain (`langchain-anthropic`)
- **Retrieval**: Top-5 chunks with MMR re-ranking (relevance + diversity)
- **Output**: Structured JSON with escalation level, recommendations, disclaimer
- **Safety**: Keyword-based emergency detection overrides LLM escalation
- **Escalation levels**: none → mild → urgent → emergency

---

## API Documentation

After starting the backend, visit: `http://localhost:8000/docs`

---

## Key Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) |
| `SECRET_KEY` | JWT signing secret (min 32 chars, required) |
| `DATABASE_URL` | PostgreSQL connection string |
| `MINIO_*` | MinIO configuration |
| `RAG_TOP_K` | Number of chunks retrieved per query (default: 5) |
| `RAG_SIMILARITY_THRESHOLD` | Min cosine similarity to include a chunk (default: 0.35) |
