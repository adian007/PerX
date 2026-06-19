"""Pytest fixtures for database integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
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


@pytest_asyncio.fixture(scope="session", autouse=True)
async def ensure_test_schema(database_url: str) -> AsyncGenerator[None, None]:
    """Ensure auth-related schema additions exist for integration tests."""

    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                ALTER TABLE employer_organizations
                    ADD COLUMN IF NOT EXISTS invite_code VARCHAR(32);
                """
            )
        )
        await connection.execute(
            text(
                """
                UPDATE employer_organizations
                SET invite_code = 'PERX-' || UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 6))
                WHERE invite_code IS NULL;
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE employer_organizations
                    ALTER COLUMN invite_code SET NOT NULL;
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_employer_invite_code
                    ON employer_organizations(invite_code);
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION update_employee_interaction_count() RETURNS TRIGGER AS $$
                DECLARE
                    warm_threshold INTEGER;
                BEGIN
                    IF NEW.interaction_type NOT IN ('select', 'reject', 'add_to_wishlist', 'redeem') THEN
                        RETURN NEW;
                    END IF;
                    warm_threshold := COALESCE(
                        (SELECT current_setting('app.recommender_warm_threshold', TRUE))::INTEGER,
                        10
                    );
                    UPDATE employee_profiles
                    SET
                        interaction_count = interaction_count + 1,
                        recommender_mode = CASE
                            WHEN (interaction_count + 1) >= warm_threshold THEN 'warm'
                            ELSE recommender_mode
                        END,
                        updated_at = NOW()
                    WHERE id = NEW.employee_id;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
    await engine.dispose()
    yield


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
