import math

import httpx

from services.retrieval_service.app.core.config import settings


class EmbeddingError(Exception):
    pass


class EmbeddingService:

    def __init__(self):
        self.api_url = settings.embedding_api_url
        self.dimension = settings.embedding_dimension

    async def embed_query(self, query: str) -> list[float]:
        if not query or not query.strip():
            raise ValueError("Query must not be empty.")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    json={"input": f"{settings.embedding_query_prefix}{query}"},
                )

                response.raise_for_status()
                payload = response.json()

        except httpx.TimeoutException as exc:
            raise EmbeddingError(
                "Embedding API request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise EmbeddingError(
                f"Embedding API returned HTTP {exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise EmbeddingError(
                "Could not connect to the embedding API."
            ) from exc

        except ValueError as exc:
            raise EmbeddingError(
                "Embedding API returned invalid JSON."
            ) from exc

        data = payload.get("data")

        if not isinstance(data, list) or len(data) != 1:
            raise EmbeddingError(
                "Expected exactly one embedding in the API response."
            )

        vector = data[0].get("embedding")

        if not isinstance(vector, list):
            raise EmbeddingError("Invalid embedding vector.")

        if len(vector) != self.dimension:
            raise EmbeddingError(
                f"Expected {self.dimension} dimensions, "
                f"received {len(vector)}."
            )

        try:
            vector = [float(value) for value in vector]
        except (TypeError, ValueError) as exc:
            raise EmbeddingError(
                "Embedding contains non-numeric values."
            ) from exc

        if not all(math.isfinite(value) for value in vector):
            raise EmbeddingError(
                "Embedding contains invalid numeric values."
            )

        return vector