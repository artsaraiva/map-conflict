import asyncio

from sqlalchemy import text

from backend.core.database import Base, engine
from backend.models.event import Article, Event  # noqa: F401


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await connection.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
