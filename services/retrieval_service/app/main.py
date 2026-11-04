from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from services.retrieval_service.app.api.retrieval import router as retrieval_router
from services.retrieval_service.app.core.database import (
    check_database_connection,
    engine,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Retrieval Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(retrieval_router)


@app.get("/health/")
async def health_check():
    try:
        await check_database_connection()

        return {
            "status": "healthy",
            "service": "retrieval-service",
            "database": "connected",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed.",
        ) from exc