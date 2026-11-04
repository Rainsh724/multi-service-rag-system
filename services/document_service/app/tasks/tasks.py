import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from services.document_service.app.core.config import settings
from services.document_service.app.core.database import (
    AsyncSessionLocal,
    engine,
)
from services.document_service.app.repositories.document_repository import (
    DocumentRepository,
)
from services.document_service.app.services.pdf_extractor import (
    PDFExtractor,
)
from services.document_service.app.services.text_cleaner import (
    TextCleaner,
)
from services.document_service.app.services.chunker import (
    TextChunker,
)
from services.document_service.app.services.embedding_service import (
    EmbeddingService,
)
from services.document_service.app.clients.retrieval_client import (
    RetrievalClient,
)
from shared.schemas.common import DocumentStatus
from shared.schemas.retrieval import ChunkInput

from services.document_service.app.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)


async def _process_document(document_id: UUID) -> dict:
    repository = DocumentRepository()
    extractor = PDFExtractor()
    cleaner = TextCleaner()
    chunker = TextChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    embedding_service = EmbeddingService()
    retrieval_client = RetrievalClient()

    async with AsyncSessionLocal() as session:
        document = await repository.get_by_id(
            session,
            document_id,
        )

        if document is None:
            raise ValueError(
                f"Document not found: {document_id}"
            )

        if document.status == DocumentStatus.COMPLETED.value:
            return {
                "document_id": str(document_id),
                "status": DocumentStatus.COMPLETED.value,
                "message": "Document was already processed.",
            }

        storage_path = document.storage_path
        filename = document.filename

        await repository.update_status(
            session,
            document,
            status=DocumentStatus.PROCESSING.value,
            error_message=None,
        )

    try:
        extracted_pages = extractor.extract(storage_path)

        cleaned_pages = [
            type(page)(
                page_number=page.page_number,
                text=cleaner.clean(page.text),
            )
            for page in extracted_pages
        ]

        chunks = chunker.chunk_pages(cleaned_pages)

        if not chunks:
            raise ValueError(
                "No text chunks were generated."
            )

        texts = [
            chunk.text
            for chunk in chunks
        ]

        embeddings = await embedding_service.embed_texts(
            texts
        )

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Embedding count does not match chunk count."
            )

        chunk_inputs = [
            ChunkInput(
                chunk_id=uuid4(),
                text=chunk.text,
                embedding=embedding,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
            )
            for chunk, embedding in zip(
                chunks,
                embeddings,
            )
        ]

        index_response = await retrieval_client.index_document(
            document_id=document_id,
            filename=filename,
            chunks=chunk_inputs,
        )

        if index_response.document_id != document_id:
            raise ValueError(
                "Retrieval Service returned an unexpected document ID."
            )

        if index_response.indexed_count != len(chunk_inputs):
            raise ValueError(
                "Indexed chunk count does not match submitted chunk count."
            )

        async with AsyncSessionLocal() as session:
            document = await repository.get_by_id(
                session,
                document_id,
            )

            if document is None:
                raise ValueError(
                    f"Document not found: {document_id}"
                )

            await repository.update_status(
                session,
                document,
                status=DocumentStatus.COMPLETED.value,
                error_message=None,
                page_count=len(cleaned_pages),
                processed_at=datetime.now(timezone.utc),
            )

        logger.info(
            "Document indexed successfully: id=%s pages=%s chunks=%s",
            document_id,
            len(cleaned_pages),
            len(chunk_inputs),
        )

        return {
            "document_id": str(document_id),
            "status": DocumentStatus.COMPLETED.value,
            "page_count": len(cleaned_pages),
            "chunk_count": len(chunk_inputs),
            "indexed_count": index_response.indexed_count,
        }

    except Exception as exc:
        logger.exception(
            "Document processing failed: %s",
            document_id,
        )

        try:
            async with AsyncSessionLocal() as session:
                document = await repository.get_by_id(
                    session,
                    document_id,
                )

                if document is not None:
                    await repository.update_status(
                        session,
                        document,
                        status=DocumentStatus.FAILED.value,
                        error_message=str(exc)[:2000],
                        processed_at=datetime.now(timezone.utc),
                    )

        except Exception:
            logger.exception(
                "Failed to update document status: %s",
                document_id,
            )

        raise


@celery_app.task(
    name="document_service.process_document",
)
def process_document_task(document_id: str) -> dict:
    async def run():
        try:
            return await _process_document(
                UUID(document_id)
            )
        finally:
            await engine.dispose()

    return asyncio.run(run())
