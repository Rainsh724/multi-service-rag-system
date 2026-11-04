from uuid import UUID

from pydantic import Field

from shared.schemas.common import BaseSchema


class ChunkInput(BaseSchema):
    chunk_id: UUID
    text: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)
    page_number: int = Field(ge=1)
    chunk_index: int = Field(ge=0)


class IndexRequest(BaseSchema):
    document_id: UUID
    filename: str
    chunks: list[ChunkInput] = Field(min_length=1)


class IndexResponse(BaseSchema):
    document_id: UUID
    indexed_count: int


class RetrievalSearchRequest(BaseSchema):
    query: str = Field(min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_ids: list[UUID] | None = None


class RetrievedChunk(BaseSchema):
    chunk_id: UUID
    document_id: UUID
    filename: str
    text: str
    page_number: int
    chunk_index: int
    similarity: float | None = None


class RetrievalSearchResponse(BaseSchema):
    query: str
    matches: list[RetrievedChunk]


class DocumentChunksRequest(BaseSchema):
    document_id: UUID


class DocumentChunksResponse(BaseSchema):
    document_id: UUID
    chunks: list[RetrievedChunk]