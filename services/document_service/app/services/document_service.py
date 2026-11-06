import logging
from uuid import uuid4, UUID

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.document_service.app.clients.retrieval_client import (
    RetrievalClient,
    RetrievalServiceError,
)
from services.document_service.app.models.document import Document
from services.document_service.app.repositories.document_repository import (
    DocumentRepository,
)
from services.document_service.app.services.file_storage import FileStorage
from shared.schemas.common import DocumentStatus


logger = logging.getLogger(__name__)


class DuplicateDocumentError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class DocumentDeletionConflictError(Exception):
    pass


class DocumentService:

    def __init__(self):
        self.repository = DocumentRepository()
        self.storage = FileStorage()
        self.retrieval_client = RetrievalClient()

    async def upload(
        self,
        session: AsyncSession,
        file: UploadFile,
    ) -> Document:
        document_id = uuid4()
        storage_path = None

        try:
            storage_path, file_hash = await self.storage.save(
                file,
                document_id,
            )

            existing = await self.repository.get_by_hash(
                session,
                file_hash,
            )

            if existing:
                await self.storage.delete(storage_path)
                raise DuplicateDocumentError(
                    "This document has already been uploaded."
                )

            document = Document(
                id=document_id,
                filename=file.filename or "document.pdf",
                file_hash=file_hash,
                storage_path=storage_path,
                status=DocumentStatus.PENDING.value,
            )

            return await self.repository.create(session, document)

        except IntegrityError:
            await session.rollback()

            if storage_path:
                await self.storage.delete(storage_path)

            raise DuplicateDocumentError(
                "This document has already been uploaded."
            )

        except Exception:
            if storage_path:
                await self.storage.delete(storage_path)

            raise

    async def delete_document(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> None:
        document = await self.repository.get_by_id(
            session,
            document_id,
        )

        if document is None:
            raise DocumentNotFoundError("Document not found.")

        if document.status in {
            DocumentStatus.PENDING.value,
            DocumentStatus.PROCESSING.value,
        }:
            raise DocumentDeletionConflictError(
                "A pending or processing document cannot be deleted."
            )

        storage_path = document.storage_path

        # Keep the document record and PDF intact if Retrieval Service
        # cannot confirm deletion of its chunks.
        await self.retrieval_client.delete_document_chunks(document_id)

        await self.repository.delete(session, document)

        try:
            await self.storage.delete(storage_path)
        except OSError:
            logger.exception(
                "Document record and chunks were deleted, but PDF cleanup failed: %s",
                document_id,
            )
