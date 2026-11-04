from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.document_service.app.models.document import Document
from services.document_service.app.repositories.document_repository import (
    DocumentRepository,
)
from services.document_service.app.services.file_storage import FileStorage
from shared.schemas.common import DocumentStatus


class DuplicateDocumentError(Exception):
    pass


class DocumentService:

    def __init__(self):
        self.repository = DocumentRepository()
        self.storage = FileStorage()

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