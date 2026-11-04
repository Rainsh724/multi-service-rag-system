from datetime import datetime
from uuid import UUID

from pydantic import Field

from shared.schemas.common import BaseSchema, DocumentStatus


class DocumentUploadResponse(BaseSchema):
    document_id: UUID
    filename: str
    status: DocumentStatus


class DocumentStatusResponse(BaseSchema):
    document_id: UUID
    filename: str
    status: DocumentStatus
    created_at: datetime
    processed_at: datetime | None = None
    error_message: str | None = None


class DocumentMetadata(BaseSchema):
    document_id: UUID
    filename: str
    page_count: int = Field(ge=0)