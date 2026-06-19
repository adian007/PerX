"""Pytest fixtures for database integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Base

# Import models so metadata is populated.
import app.models  # noqa: F401


@pytest.fixture(scope="session")
def database_url() -> str:
    """Resolve async Postgres URL for tests."""

    return os.getenv(
        "DATABASE_URL",
        get_settings().database_url,
    )


@pytest_asyncio.fixture
async def db_session(database_url: str) -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async session rolled back after each test."""

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = session_factory(bind=connection)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()

    await engine.dispose()
