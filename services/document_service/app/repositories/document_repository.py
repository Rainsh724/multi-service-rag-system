from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.document_service.app.models.document import Document


class DocumentRepository:

    @staticmethod
    async def create(
        session: AsyncSession,
        document: Document,
    ) -> Document:
        session.add(document)
        await session.commit()
        await session.refresh(document)

        return document

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        document_id: UUID,
    ) -> Document | None:
        return await session.get(Document, document_id)

    @staticmethod
    async def get_by_hash(
        session: AsyncSession,
        file_hash: str,
    ) -> Document | None:
        result = await session.execute(
            select(Document).where(
                Document.file_hash == file_hash
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def delete(
        session: AsyncSession,
        document: Document,
    ) -> None:
        try:
            await session.delete(document)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    @staticmethod
    async def update_status(
        session: AsyncSession,
        document: Document,
        status: str,
        error_message: str | None = None,
        page_count: int | None = None,
        processed_at=None,
    ) -> Document:
        document.status = status
        document.error_message = error_message

        if page_count is not None:
            document.page_count = page_count

        if processed_at is not None:
            document.processed_at = processed_at

        await session.commit()
        await session.refresh(document)

        return document
