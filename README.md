# Multi-Service Persian RAG System

A three-service Retrieval-Augmented Generation (RAG) application for uploading Persian PDF documents, processing them asynchronously, retrieving semantically relevant chunks, and answering questions with page-level source references.

## Architecture

| Component | Responsibility | Local URL |
|---|---|---|
| Document Service | PDF upload, extraction, cleaning, chunking, embeddings and async processing | http://127.0.0.1:8001 |
| Retrieval Service | PostgreSQL/pgvector indexing and semantic Top-K search | http://127.0.0.1:8002 |
| RAG Orchestrator | LangGraph workflow, context evaluation and answer generation | http://127.0.0.1:8000 |
| PostgreSQL + pgvector | Document metadata and vector storage | 127.0.0.1:5433 |
| Redis | Celery broker and result backend | 127.0.0.1:6379 |
| Celery Worker | Asynchronous PDF processing | Internal Docker network |
| Web UI | Persian PDF upload, processing status and document Q&A | http://127.0.0.1:5173 |

All backend services, the Celery worker, PostgreSQL and Redis run as separate Docker Compose services. The frontend remains a local Vite development server.

### RAG workflow

1. A PDF is uploaded through the Document Service.
2. Celery processes it asynchronously: extraction → cleaning → chunking → embedding.
3. The Document Service sends chunks and metadata to the Retrieval Service.
4. The Retrieval Service stores vectors in PostgreSQL with pgvector.
5. A question is embedded and relevant chunks are retrieved.
6. LangGraph evaluates whether the retrieved context is sufficient.
7. The system generates an answer with source references, or abstains when context is insufficient.

## Requirements

- Docker Desktop / Docker Engine with Docker Compose
- Node.js 20+ and npm (for the frontend)
- An OpenAI-compatible chat model endpoint and an embedding endpoint

## Configuration

From the repository root:

```powershell
Copy-Item .env.example .env
```

Set a non-default `POSTGRES_PASSWORD`, and configure `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `EMBEDDING_API_URL`, and `EMBEDDING_DIMENSION` in `.env`.

The embedding service and Retrieval Service must use the same embedding model and vector dimension. The current schema is configured for 768-dimensional vectors.

## Run the full backend with Docker Compose

Run from the repository root:

```powershell
Copy-Item .env.example .env
# Edit .env and set POSTGRES_PASSWORD and your LLM credentials.
docker compose config
docker compose up --build -d
docker compose ps
```

Compose builds and starts PostgreSQL, Redis, Retrieval Service, Document Service, the Celery Worker and RAG Service. The retrieval tables are initialized during service startup; Document Service creates its metadata tables on startup. Health checks and dependency conditions control startup order.

API documentation:

- Document Service: http://127.0.0.1:8001/docs
- Retrieval Service: http://127.0.0.1:8002/docs
- RAG Orchestrator: http://127.0.0.1:8000/docs

Check logs:

```powershell
docker compose logs -f document-service retrieval-service rag-service celery-worker
```

Stop the stack without deleting persistent data:

```powershell
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the PostgreSQL, Redis and document-storage volumes.

## Run the frontend

The Vite development server runs on the host and proxies API requests to the published localhost ports:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173.

## Local Python development (optional)

For debugging a backend service directly on Windows, stop its corresponding Compose container first to avoid a port conflict. Start PostgreSQL and Redis with Compose, then use a Python 3.12 virtual environment and install each service's requirements file. The local-host URLs in `.env.example` are intended for this mode; Compose overrides database, Redis and inter-service URLs with Docker DNS names.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/documents/upload/` | Upload a PDF (multipart field: `file`) |
| GET | `/documents/{document_id}/status/` | Read asynchronous processing status |
| POST | `/retrieval/search/` | Semantic vector search |
| POST | `/rag/ask/` | Ask a question and receive answer plus sources |
| GET | `/health/` | Service health check |

## Tests

Run unit tests from the repository root in a configured Python environment:

```powershell
python -m pytest tests/unit -v
```

Some tests may require external services or environment configuration depending on the test implementation.

## Notes

- PDF processing is asynchronous; a successful upload means the job was accepted, not that indexing has finished.
- Ask questions only after the document status becomes `completed`.
- The web UI is a lightweight development interface, not a production deployment. Authentication, authorization, production CORS policy, rate limiting and deployment hardening are outside its current scope.
- Do not commit your real `.env` file or API credentials.
