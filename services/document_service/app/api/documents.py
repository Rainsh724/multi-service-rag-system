from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from services.document_service.app.core.database import get_db
from services.document_service.app.repositories.document_repository import (
    DocumentRepository,
)
from services.document_service.app.services.document_service import (
    DocumentService,
    DuplicateDocumentError,
    DocumentNotFoundError,
    DocumentDeletionConflictError,
)
from services.document_service.app.models.document import DocumentChat
from shared.schemas.documents import (
    DocumentUploadResponse,
    DocumentStatusResponse,
)
from shared.schemas.common import DocumentStatus
from services.document_service.app.tasks.tasks import process_document_task

router = APIRouter(prefix="/documents", tags=["Documents"])
document_service = DocumentService()
repository = DocumentRepository()


def _serialize_document(document):
    return {
        "document_id": str(document.id),
        "filename": document.filename,
        "status": document.status,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "processed_at": document.processed_at.isoformat() if document.processed_at else None,
        "error_message": document.error_message,
        "page_count": document.page_count,
    }


@router.get("/")
async def list_documents(session: AsyncSession = Depends(get_db)):
    documents = await repository.list_all(session)
    return [_serialize_document(document) for document in documents]


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
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Invalid file content type.")

    try:
        document = await document_service.upload(session, file)
        await repository.create_chat(session, document.id)

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
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        await file.close()


@router.get("/{document_id}/status/", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    document = await repository.get_by_id(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentStatusResponse(
        document_id=document.id,
        filename=document.filename,
        status=DocumentStatus(document.status),
        created_at=document.created_at,
        processed_at=document.processed_at,
        error_message=document.error_message,
    )


@router.get("/{document_id}/chat/")
async def get_document_chat(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    document = await repository.get_by_id(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chat = await repository.get_chat_by_document(session, document_id)
    if chat is None:
        chat = await repository.create_chat(session, document_id)
        chat = await repository.get_chat_by_document(session, document_id)

    return {
        "chat_id": str(chat.id),
        "document_id": str(document_id),
        "messages": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "sources": message.sources or [],
                "insufficient_context": message.insufficient_context,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in chat.messages
        ],
    }


@router.post("/{document_id}/chat/messages/")
async def save_chat_message(
    document_id: UUID,
    payload: dict,
    session: AsyncSession = Depends(get_db),
):
    document = await repository.get_by_id(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    role = payload.get("role")
    content = payload.get("content")
    if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=422, detail="Invalid chat message.")

    chat = await repository.get_chat_by_document(session, document_id)
    if chat is None:
        chat = await repository.create_chat(session, document_id)

    message = await repository.add_chat_message(
        session=session,
        chat_id=chat.id,
        role=role,
        content=content,
        sources=payload.get("sources") or [],
        insufficient_context=bool(payload.get("insufficient_context", False)),
    )
    return {"message_id": str(message.id)}


@router.delete("/{document_id}/chat/")
async def delete_document_chat(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    document = await repository.get_by_id(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chat = await repository.get_chat_by_document(session, document_id)
    if chat is not None:
        await repository.delete_chat(session, chat)

    return {"document_id": str(document_id), "message": "Chat history deleted."}


@router.delete("/{document_id}/")
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    try:
        await document_service.delete_document(session=session, document_id=document_id)
        return {
            "document_id": str(document_id),
            "message": "Document, chat history, and indexed chunks were deleted.",
        }
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentDeletionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Document deletion failed. The document was not fully deleted.",
        ) from exc


@router.post(
    "/{document_id}/reprocess/",
    response_model=DocumentUploadResponse,
    status_code=202,
)
async def reprocess_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    document = await repository.get_by_id(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(status_code=409, detail="Document is already being processed.")

    await repository.update_status(
        session,
        document,
        status=DocumentStatus.PENDING.value,
        error_message=None,
        processed_at=None,
    )

    try:
        process_document_task.delay(str(document.id))
    except Exception as exc:
        await repository.update_status(
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
