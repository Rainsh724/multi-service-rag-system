from uuid import uuid4

import pytest
from pydantic import ValidationError

from shared.schemas import (
    DocumentStatus,
    DocumentUploadResponse,
    RetrievalSearchRequest,
    RAGRequest,
)


def test_document_upload_response():
    response = DocumentUploadResponse(
        document_id=uuid4(),
        filename="sample.pdf",
        status=DocumentStatus.PENDING,
    )

    assert response.status == DocumentStatus.PENDING


def test_retrieval_default_top_k():
    request = RetrievalSearchRequest(
        query="What is machine learning?"
    )

    assert request.top_k == 5


def test_retrieval_rejects_invalid_top_k():
    with pytest.raises(ValidationError):
        RetrievalSearchRequest(
            query="Test",
            top_k=100,
        )


def test_rag_request():
    request = RAGRequest(
        question="Explain artificial intelligence."
    )

    assert request.top_k == 5
    assert request.document_ids is None