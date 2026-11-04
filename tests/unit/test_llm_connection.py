import asyncio

from services.rag_service.app.clients.llm_client import LLMClient


async def main():
    llm = LLMClient()

    response = await llm.generate(
        system_prompt="You are a helpful assistant. Answer in Persian.",
        user_prompt="در یک جمله توضیح بده RAG چیست.",
    )

    print("LLM response:")
    print(response)

    await llm.client.close()


if __name__ == "__main__":
    asyncio.run(main())