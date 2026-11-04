from uuid import UUID

from pydantic import Field

from shared.schemas.common import BaseSchema


class RAGRequest(BaseSchema):
    question: str = Field(min_length=1, max_length=5000)
    document_ids: list[UUID] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SourceReference(BaseSchema):
    document_id: UUID
    filename: str
    page_number: int
    chunk_id: UUID


class RAGResponse(BaseSchema):
    question: str
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    insufficient_context: bool = False