import pytest

from services.document_service.app.services.embedding_service import (
    EmbeddingService,
)


@pytest.mark.asyncio
async def test_embedding_api_batch():
    service = EmbeddingService()

    texts = [
        "هوش مصنوعی در تحلیل داده‌ها کاربرد دارد.",
        "یادگیری ماشین یکی از شاخه‌های هوش مصنوعی است.",
    ]

    embeddings = await service.embed_texts(texts)

    assert len(embeddings) == 2

    for embedding in embeddings:
        assert len(embedding) == 768
        assert all(isinstance(value, float) for value in embedding)

    print("Number of embeddings:", len(embeddings))
    print("Embedding dimension:", len(embeddings[0]))