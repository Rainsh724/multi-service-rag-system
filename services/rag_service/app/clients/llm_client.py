from openai import AsyncOpenAI

from services.rag_service.app.core.config import settings


class LLMClientError(Exception):
    pass


class LLMClient:

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base_url,
            timeout=90.0,
            max_retries=2,
        )

        self.model = settings.llm_model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.2,
            )

            content = response.choices[0].message.content

            if not content or not content.strip():
                raise LLMClientError(
                    "LLM returned an empty response."
                )

            return content.strip()

        except LLMClientError:
            raise

        except Exception as exc:
            raise LLMClientError(
                "LLM generation failed."
            ) from exc