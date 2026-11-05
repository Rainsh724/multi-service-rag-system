from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from services.document_service.app.core.database import get_db
from services.document_service.app.services.document_service import (
    DocumentService,
    DuplicateDocumentError,
)
from shared.schemas.documents import DocumentUploadResponse
from shared.schemas.common import DocumentStatus
from uuid import UUID

from shared.schemas.documents import DocumentStatusResponse

from services.document_service.app.tasks.tasks import (
    process_document_task,
)

router = APIRouter(prefix="/documents", tags=["Documents"])

document_service = DocumentService()


@router.post(
    "/upload/",
    response_model=DocumentUploadResponse,
    status_code=202,
)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file content type.",
        )

    try:
        document = await document_service.upload(session, file)
        try:
            process_document_task.delay(str(document.id))
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Document was uploaded but processing could not be scheduled.",
            ) from exc

        return DocumentUploadResponse(
            document_id=document.id,
            filename=document.filename,
            status=DocumentStatus(document.status),
        )

    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    finally:
        await file.close()


@router.get(
    "/{document_id}/status/",
    response_model=DocumentStatusResponse,
)
async def get_document_status(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    document = await document_service.repository.get_by_id(
        session,
        document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return DocumentStatusResponse(
        document_id=document.id,
        filename=document.filename,
        status=DocumentStatus(document.status),
        created_at=document.created_at,
        processed_at=document.processed_at,
        error_message=document.error_message,
    )

@router.post(
    "/{document_id}/reprocess/",
    response_model=DocumentUploadResponse,
    status_code=202,
)
async def reprocess_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    document = await document_service.repository.get_by_id(
        session,
        document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=409,
            detail="Document is already being processed.",
        )

    await document_service.repository.update_status(
        session,
        document,
        status=DocumentStatus.PENDING.value,
        error_message=None,
        processed_at=None,
    )

    try:
        process_document_task.delay(str(document.id))
    except Exception as exc:
        await document_service.repository.update_status(
            session,
            document,
            status=DocumentStatus.FAILED.value,
            error_message="Could not schedule document reprocessing.",
        )
        raise HTTPException(
            status_code=503,
            detail="Document reprocessing could not be scheduled.",
        ) from exc

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=DocumentStatus.PENDING,
    )
