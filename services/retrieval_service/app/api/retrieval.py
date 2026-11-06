from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.retrieval_service.app.core.config import settings
from services.retrieval_service.app.core.database import get_db
from services.retrieval_service.app.repositories.chunk_repository import (
    ChunkRepository,
)
from services.retrieval_service.app.services.embedding_service import (
    EmbeddingError,
    EmbeddingService,
)

from shared.schemas.retrieval import (
    IndexRequest,
    IndexResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievedChunk,
    DocumentChunksResponse,
)

router = APIRouter(tags=["Retrieval"])

repository = ChunkRepository()
embedding_service = EmbeddingService()


@router.post(
    "/internal/index/",
    response_model=IndexResponse,
)
async def index_document(
    request: IndexRequest,
    session: AsyncSession = Depends(get_db),
):
    chunk_indices = [
        chunk.chunk_index
        for chunk in request.chunks
    ]

    if len(chunk_indices) != len(set(chunk_indices)):
        raise HTTPException(
            status_code=422,
            detail="Duplicate chunk_index values in request.",
        )

    for chunk in request.chunks:
        if len(chunk.embedding) != settings.embedding_dimension:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid embedding dimension for chunk "
                    f"{chunk.chunk_id}. Expected "
                    f"{settings.embedding_dimension}."
                ),
            )

    try:
        indexed_count = await repository.index_chunks(
            session,
            request,
        )

        return IndexResponse(
            document_id=request.document_id,
            indexed_count=indexed_count,
        )

    except Exception as exc:
        await session.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to index document chunks.",
        ) from exc


@router.delete(
    "/internal/documents/{document_id}/chunks/",
)
async def delete_document_chunks(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    try:
        deleted_count = await repository.delete_document_chunks(
            session=session,
            document_id=document_id,
        )
        return {
            "document_id": str(document_id),
            "deleted_count": deleted_count,
        }
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete document chunks.",
        ) from exc


@router.post(
    "/search/",
    response_model=RetrievalSearchResponse,
)
async def search_chunks(
    request: RetrievalSearchRequest,
    session: AsyncSession = Depends(get_db),
):
    try:
        query_embedding = await embedding_service.embed_query(
            request.query
        )

        results = await repository.search(
            session=session,
            query_embedding=query_embedding,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )

        matches = [
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                filename=chunk.filename,
                text=chunk.text,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                similarity=similarity,
            )
            for chunk, similarity in results
        ]

        return RetrievalSearchResponse(
            query=request.query,
            matches=matches,
        )

    except EmbeddingError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Retrieval search failed.",
        ) from exc


@router.get(
    "/documents/{document_id}/chunks/",
    response_model=DocumentChunksResponse,
)
async def get_document_chunks(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    try:
        chunks = await repository.get_document_chunks(
            session=session,
            document_id=document_id,
        )

        return DocumentChunksResponse(
            document_id=document_id,
            chunks=[
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    similarity=None,
                )
                for chunk in chunks
            ],
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document chunks.",
        ) from exc
