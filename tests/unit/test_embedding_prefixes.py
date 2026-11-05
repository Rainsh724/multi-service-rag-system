import pytest

from services.document_service.app.services import embedding_service as document_module
from services.retrieval_service.app.services import embedding_service as retrieval_module


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.payloads = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json):
        self.payloads.append(json)
        vectors = json["input"]
        if isinstance(vectors, str):
            vectors = [vectors]
        return FakeResponse({
            "data": [
                {"index": index, "embedding": [0.1, 0.2, 0.3]}
                for index, _ in enumerate(vectors)
            ]
        })


@pytest.mark.asyncio
async def test_document_embeddings_use_passage_prefix(monkeypatch):
    clients = []

    def client_factory(*args, **kwargs):
        client = FakeAsyncClient(*args, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(document_module.httpx, "AsyncClient", client_factory)
    service = document_module.EmbeddingService()
    service.dimension = 3
    service.batch_size = 8

    result = await service.embed_texts(["متن سند"])

    assert result == [[0.1, 0.2, 0.3]]
    assert clients[0].payloads == [{"input": ["passage: متن سند"]}]


@pytest.mark.asyncio
async def test_query_embeddings_use_query_prefix(monkeypatch):
    clients = []

    def client_factory(*args, **kwargs):
        client = FakeAsyncClient(*args, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(retrieval_module.httpx, "AsyncClient", client_factory)
    service = retrieval_module.EmbeddingService()
    service.dimension = 3

    result = await service.embed_query("ویژگی‌های پهپاد چیست؟")

    assert result == [0.1, 0.2, 0.3]
    assert clients[0].payloads == [{"input": "query: ویژگی‌های پهپاد چیست؟"}]
