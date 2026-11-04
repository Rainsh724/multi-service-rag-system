import pytest

from services.document_service.app.services.embedding_service import (
    EmbeddingError,
    EmbeddingService,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    async def post(self, url, json):
        return FakeResponse(self.payload)


@pytest.mark.asyncio
async def test_embedding_batch_validates_and_orders_vectors():
    service = EmbeddingService()
    service.dimension = 3

    client = FakeClient({
        "data": [
            {"index": 1, "embedding": [4, 5, 6]},
            {"index": 0, "embedding": [1, 2, 3]},
        ]
    })

    vectors = await service._embed_batch(client, ["first", "second"])

    assert vectors == [
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
    ]


@pytest.mark.asyncio
async def test_embedding_rejects_non_object_response():
    service = EmbeddingService()
    client = FakeClient(["not", "an", "object"])

    with pytest.raises(EmbeddingError, match="JSON object"):
        await service._embed_batch(client, ["text"])


@pytest.mark.asyncio
async def test_embedding_rejects_non_finite_values():
    service = EmbeddingService()
    service.dimension = 2
    client = FakeClient({
        "data": [
            {"index": 0, "embedding": [1.0, float("inf")]}
        ]
    })

    with pytest.raises(EmbeddingError, match="invalid numeric"):
        await service._embed_batch(client, ["text"])


@pytest.mark.asyncio
async def test_embedding_rejects_duplicate_indices():
    service = EmbeddingService()
    service.dimension = 1
    client = FakeClient({
        "data": [
            {"index": 0, "embedding": [1]},
            {"index": 0, "embedding": [2]},
        ]
    })

    with pytest.raises(EmbeddingError, match="Duplicate"):
        await service._embed_batch(client, ["first", "second"])
