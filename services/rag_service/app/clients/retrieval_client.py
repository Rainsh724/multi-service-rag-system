import httpx

from services.rag_service.app.core.config import settings
from shared.schemas.retrieval import (
    DocumentChunksResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)


class RetrievalClientError(Exception):
    pass


class RetrievalClient:

    def __init__(self):
        self.base_url = settings.retrieval_service_url.rstrip("/")
        self.timeout = 60.0

    async def search(
        self,
        query: str,
        top_k: int,
        document_ids=None,
    ) -> RetrievalSearchResponse:

        request = RetrievalSearchRequest(
            query=query,
            top_k=top_k,
            document_ids=document_ids,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,
            ) as client:

                response = await client.post(
                    f"{self.base_url}/search/",
                    json=request.model_dump(mode="json"),
                )

                response.raise_for_status()

                return RetrievalSearchResponse.model_validate(
                    response.json()
                )

        except httpx.TimeoutException as exc:
            raise RetrievalClientError(
                "Retrieval Service request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise RetrievalClientError(
                f"Retrieval Service returned HTTP "
                f"{exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise RetrievalClientError(
                "Could not connect to Retrieval Service."
            ) from exc

        except ValueError as exc:
            raise RetrievalClientError(
                "Invalid response from Retrieval Service."
            ) from exc

    async def get_document_chunks(
        self,
        document_id: str,
    ) -> DocumentChunksResponse:

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,
            ) as client:

                response = await client.get(
                    f"{self.base_url}/documents/{document_id}/chunks/",
                )

                response.raise_for_status()

                return DocumentChunksResponse.model_validate(
                    response.json()
                )

        except httpx.TimeoutException as exc:
            raise RetrievalClientError(
                "Document retrieval request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise RetrievalClientError(
                f"Retrieval Service returned HTTP "
                f"{exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise RetrievalClientError(
                "Could not connect to Retrieval Service."
            ) from exc

        except ValueError as exc:
            raise RetrievalClientError(
                "Invalid document chunks response."
            ) from exc