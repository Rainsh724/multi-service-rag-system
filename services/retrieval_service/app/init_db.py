import asyncio

from sqlalchemy import text

from services.retrieval_service.app.core.database import (
    Base,
    engine,
)
from services.retrieval_service.app.models import Chunk


async def init_db():
    async with engine.begin() as connection:
        await connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )

        await connection.run_sync(
            Base.metadata.create_all
        )

    print("Retrieval database tables created successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())