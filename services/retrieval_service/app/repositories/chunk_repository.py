from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from services.retrieval_service.app.models.chunk import Chunk
from shared.schemas.retrieval import IndexRequest


class ChunkRepository:

    @staticmethod
    async def index_chunks(
        session: AsyncSession,
        request: IndexRequest,
    ) -> int:
        records = [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": request.document_id,
                "filename": request.filename,
                "text": chunk.text,
                "embedding": chunk.embedding,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in request.chunks
        ]

        await session.execute(
            delete(Chunk).where(
                Chunk.document_id == request.document_id
            )
        )

        statement = insert(Chunk).values(records)
        result = await session.execute(statement)
        await session.commit()

        return result.rowcount or 0

    @staticmethod
    async def search(
        session: AsyncSession,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[UUID] | None = None,
    ) -> list[tuple[Chunk, float]]:
        distance = Chunk.embedding.cosine_distance(
            query_embedding
        )

        statement = select(
            Chunk,
            (1 - distance).label("similarity"),
        )

        if document_ids is not None:
            statement = statement.where(
                Chunk.document_id.in_(document_ids)
            )

        statement = (
            statement
            .order_by(distance.asc())
            .limit(top_k)
        )

        result = await session.execute(statement)

        return [
            (row[0], float(row[1]))
            for row in result.all()
        ]

    @staticmethod
    async def get_document_chunks(
        session: AsyncSession,
        document_id: UUID,
    ) -> list[Chunk]:
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(
                Chunk.page_number.asc(),
                Chunk.chunk_index.asc(),
            )
        )

        result = await session.execute(statement)

        return list(result.scalars().all())
