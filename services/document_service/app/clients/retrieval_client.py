import httpx

from services.document_service.app.core.config import settings
from shared.schemas.retrieval import (
    ChunkInput,
    IndexRequest,
    IndexResponse,
)


class RetrievalServiceError(Exception):
    pass


class RetrievalClient:

    def __init__(self):
        self.base_url = settings.retrieval_service_url.rstrip("/")
        self.timeout = 120.0

    async def index_document(
        self,
        document_id,
        filename: str,
        chunks: list[ChunkInput],
    ) -> IndexResponse:

        request = IndexRequest(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/internal/index/",
                    json=request.model_dump(mode="json"),
                )

                response.raise_for_status()

                return IndexResponse.model_validate(
                    response.json()
                )

        except httpx.TimeoutException as exc:
            raise RetrievalServiceError(
                "Retrieval Service request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise RetrievalServiceError(
                f"Retrieval Service returned HTTP "
                f"{exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise RetrievalServiceError(
                "Could not connect to Retrieval Service."
            ) from exc

        except ValueError as exc:
            raise RetrievalServiceError(
                "Retrieval Service returned an invalid response."
            ) from exc