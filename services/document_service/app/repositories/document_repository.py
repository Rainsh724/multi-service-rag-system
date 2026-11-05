from uuid import UUID

from sqlalchemy import desc, select
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
    async def list_all(
        session: AsyncSession,
    ) -> list[Document]:
        result = await session.execute(
            select(Document).order_by(desc(Document.created_at))
        )
        return list(result.scalars().all())

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

        document.processed_at = processed_at

        await session.commit()
        await session.refresh(document)

        return document
