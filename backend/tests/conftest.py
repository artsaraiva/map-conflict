"""Shared test harness: a dedicated test database next to the one DATABASE_URL names.

The test database is `<DATABASE_URL's database>_test` on the same server, so tests can
never truncate a developer's data. Its schema is rebuilt from ORM metadata once per run,
and every table is truncated before each test.
"""

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.core.config import get_settings
from backend.core.database import Base
import backend.models.event  # noqa: F401  registers the tables on Base.metadata

_app_url = make_url(get_settings().database_url)
TEST_DATABASE_URL = _app_url.set(database=f"{_app_url.database}_test")


async def _build_test_database() -> None:
    server = create_async_engine(
        _app_url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with server.connect() as connection:
        exists = await connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE_URL.database},
        )
        if not exists:
            await connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_URL.database}"'))
    await server.dispose()

    test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with test_engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await test_engine.dispose()


@pytest.fixture(scope="session")
def _test_database():
    asyncio.run(_build_test_database())


@pytest_asyncio.fixture
async def session(_test_database):
    """A session on the empty test database."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    await engine.dispose()
