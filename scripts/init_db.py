import asyncio

from services.document_service.app.core.database import Base, engine
from services.document_service.app.models import Document


async def init_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    print("Database tables created successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())