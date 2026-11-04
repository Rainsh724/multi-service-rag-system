from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from services.document_service.app.api.documents import router as documents_router
from services.document_service.app.core.database import (
    check_database_connection,
    engine,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Document Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(documents_router)


@app.get("/health/")
async def health_check():
    try:
        await check_database_connection()

        return {
            "status": "healthy",
            "service": "document-service",
            "database": "connected",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )