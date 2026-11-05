# Multi-Service Persian RAG System

A three-service Retrieval-Augmented Generation (RAG) application for uploading Persian PDF documents, processing them asynchronously, retrieving semantically relevant chunks, and answering questions with page-level source references.

## Architecture

| Component | Responsibility | Local URL |
|---|---|---|
| Document Service | PDF upload, text extraction, cleaning, chunking, embeddings, async processing | http://127.0.0.1:8001 |
| Retrieval Service | PostgreSQL/pgvector indexing and semantic Top-K search | http://127.0.0.1:8002 |
| RAG Orchestrator | LangGraph workflow, context evaluation, answer generation and abstention | http://127.0.0.1:8000 |
| PostgreSQL + pgvector | Document metadata and vector storage | 127.0.0.1:5433 |
| Redis | Celery broker and result backend | 127.0.0.1:6379 |
| Web UI | Persian PDF upload, processing status and document Q&A | http://127.0.0.1:5173 |

### RAG workflow

1. A PDF is uploaded through the Document Service.
2. Celery processes it asynchronously: extraction → cleaning → chunking → embedding.
3. The Document Service sends chunks and metadata to the Retrieval Service.
4. The Retrieval Service stores vectors in PostgreSQL with pgvector.
5. A question is embedded and relevant chunks are retrieved.
6. LangGraph evaluates whether the retrieved context is sufficient.
7. The system generates an answer with source references, or abstains when context is insufficient.

## Requirements

- Python 3.12+
- Node.js 20+ and npm
- Docker Desktop / Docker Engine
- An OpenAI-compatible chat model endpoint and an embedding endpoint

## Configuration

From the repository root:

```powershell
Copy-Item .env.example .env
```

Set the values in `.env` for your environment. In particular, configure:

- `POSTGRES_PASSWORD` and `DATABASE_URL`
- `LLM_API_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`
- `EMBEDDING_API_URL` and `EMBEDDING_DIMENSION`

The embedding service and Retrieval Service must use the same embedding model and vector dimension. The current schema is configured for 768-dimensional vectors.

## Run locally (Windows PowerShell)

### 1. Start infrastructure

```powershell
docker compose up -d
docker compose ps
```

Wait until PostgreSQL and Redis report healthy.

### 2. Create the Python environment and install service dependencies

Run from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r services/document_service/app/requirements.txt
pip install -r services/retrieval_service/app/requirements.txt
pip install -r services/rag_service/app/requirements.txt
```

### 3. Initialize databases

```powershell
python -m scripts.init_db
python -m services.retrieval_service.app.init_db
```

### 4. Start the three API services

Open separate PowerShell terminals, activate the same virtual environment in each, and run:

**Terminal 1 — Document Service**
```powershell
uvicorn services.document_service.app.main:app --host 127.0.0.1 --port 8001
```

**Terminal 2 — Retrieval Service**
```powershell
uvicorn services.retrieval_service.app.main:app --host 127.0.0.1 --port 8002
```

**Terminal 3 — RAG Orchestrator**
```powershell
uvicorn services.rag_service.app.main:app --host 127.0.0.1 --port 8000
```

### 5. Start the Celery worker

Open another terminal, activate the virtual environment, and run:

```powershell
celery -A services.document_service.app.tasks.celery_app.celery_app worker --loglevel=info --pool=solo
```

The worker is required for asynchronous PDF processing. Keep it running while uploading documents.

### 6. Start the web interface

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. The Vite development server proxies requests to the three local APIs, so separate browser CORS configuration is not needed for local development.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/documents/` | List previously uploaded documents and their processing status (newest first) |\n| POST | `/documents/upload/` | Upload a PDF (multipart field: `file`) |
| GET | `/documents/{document_id}/status/` | Read asynchronous processing status |
| POST | `/retrieval/search/` | Semantic vector search |
| POST | `/rag/ask/` | Ask a question and receive answer plus sources |
| GET | `/health/` | Service health check |

Interactive API documentation is available at:

- Document Service: http://127.0.0.1:8001/docs
- Retrieval Service: http://127.0.0.1:8002/docs
- RAG Orchestrator: http://127.0.0.1:8000/docs

## Tests

Run the local unit tests from the repository root:

```powershell
python -m pytest tests/unit -v
```

Some tests may require external services or environment configuration depending on the test implementation. Review test requirements before running tests that call live embedding or LLM APIs.

## Notes

- PDF processing is asynchronous; a successful upload means the job was accepted, not that indexing has finished.
- Ask questions only after the document status becomes `completed`.
- The web UI is a lightweight development interface, not a production deployment. Authentication, authorization, production CORS policy, rate limiting, and deployment hardening are outside its current scope.
- Do not commit your real `.env` file or API credentials.
