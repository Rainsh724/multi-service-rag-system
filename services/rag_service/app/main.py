import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)

from fastapi import FastAPI

from services.rag_service.app.api.ask import router as ask_router
from services.rag_service.app.core.config import settings


app = FastAPI(
    title="RAG Orchestrator Service",
    version="1.0.0",
    description="LangGraph-based Persian RAG API",
)

app.include_router(
    ask_router,
    prefix="/rag",
    tags=["RAG"],
)


@app.get("/health/")
async def health_check():
    return {
        "service": settings.app_name,
        "status": "healthy",
    }
