import math

import httpx

from services.document_service.app.core.config import settings


class EmbeddingError(Exception):
    """Raised when the embedding API request or response is invalid."""


class EmbeddingService:

    def __init__(self):
        self.api_url = settings.embedding_api_url
        self.dimension = settings.embedding_dimension
        self.batch_size = settings.embedding_batch_size
        self.timeout = 180.0

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        if any(
            not isinstance(text, str) or not text.strip()
            for text in texts
        ):
            raise ValueError(
                "All input texts must be non-empty strings."
            )

        if self.batch_size <= 0:
            raise EmbeddingError(
                "Embedding batch size must be greater than zero."
            )

        embeddings = []

        async with httpx.AsyncClient(
            timeout=self.timeout,
        ) as client:
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start:start + self.batch_size]

                batch_embeddings = await self._embed_batch(
                    client,
                    batch,
                )

                embeddings.extend(batch_embeddings)

        return embeddings

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        texts: list[str],
    ) -> list[list[float]]:
        try:
            response = await client.post(
                self.api_url,
                json={"input": texts},
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

        if not isinstance(payload, dict):
            raise EmbeddingError(
                "Embedding API response must be a JSON object."
            )

        data = payload.get("data")

        if not isinstance(data, list):
            raise EmbeddingError(
                "Embedding API response does not contain a valid data list."
            )

        if len(data) != len(texts):
            raise EmbeddingError(
                "Embedding count does not match input text count."
            )

        indexed_embeddings = [None] * len(texts)

        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingError(
                    "Invalid embedding item in API response."
                )

            index = item.get("index")
            vector = item.get("embedding")

            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or index < 0
                or index >= len(texts)
            ):
                raise EmbeddingError(
                    "Invalid embedding index in API response."
                )

            if indexed_embeddings[index] is not None:
                raise EmbeddingError(
                    "Duplicate embedding index in API response."
                )

            if not isinstance(vector, list):
                raise EmbeddingError(
                    "Embedding vector must be a list."
                )

            if len(vector) != self.dimension:
                raise EmbeddingError(
                    f"Expected {self.dimension} dimensions, "
                    f"received {len(vector)}."
                )

            try:
                vector = [float(value) for value in vector]
            except (TypeError, ValueError) as exc:
                raise EmbeddingError(
                    "Embedding vector contains non-numeric values."
                ) from exc

            if not all(math.isfinite(value) for value in vector):
                raise EmbeddingError(
                    "Embedding vector contains invalid numeric values."
                )

            indexed_embeddings[index] = vector

        if any(
            embedding is None
            for embedding in indexed_embeddings
        ):
            raise EmbeddingError(
                "Embedding API response is missing one or more vectors."
            )

        return indexed_embeddings
