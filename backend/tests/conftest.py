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
        await connection.execute(
            text(
                """
                ALTER TABLE refresh_tokens
                    ADD COLUMN IF NOT EXISTS lookup_hash VARCHAR(64);
                """
            )
        )
        await connection.execute(
            text(
                """
                UPDATE refresh_tokens SET is_revoked = TRUE WHERE lookup_hash IS NULL;
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_lookup_hash
                    ON refresh_tokens(lookup_hash)
                    WHERE lookup_hash IS NOT NULL;
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS vision_jobs (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    task VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'queued',
                    request_payload JSONB NOT NULL DEFAULT '{}',
                    result_payload JSONB,
                    error_payload JSONB,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMP WITH TIME ZONE,
                    expires_at TIMESTAMP WITH TIME ZONE
                );
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS achievements (
                    slug VARCHAR(50) PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    requirement TEXT NOT NULL,
                    interactive BOOLEAN NOT NULL DEFAULT FALSE,
                    goal INTEGER
                );
                """
            )
        )
        await connection.execute(
            text(
                """
                INSERT INTO achievements (slug, title, description, requirement, interactive, goal) VALUES
                    ('first-steps', 'Hapat e parë', 'Përfundo hapin e parë të rrugës së përfitimeve.', 'Përfundo çdo milestone udhëtimi', FALSE, NULL),
                    ('globe-trotter', 'Eksplorues global', 'Eksploro përfitime në 4 kategori të ndryshme.', 'Vizito 4 kategori në Eksploro', FALSE, NULL),
                    ('wishlist-curator', 'Kurues i të ruajturave', 'Shto 5 përfitime te të ruajturat.', '5 artikuj të ruajtur', FALSE, NULL),
                    ('smart-spender', 'Zgjedhës i zgjuar', 'Zgjidh një përfitim me bonus pyetësorë.', 'Përfundo rrjedhën Pyetësorë + Zgjidh', FALSE, NULL),
                    ('well-rounded', 'I balancuar', 'Përfundo të gjitha hapat e rrugës.', 'Të 4 hapat e rrugës', FALSE, NULL),
                    ('budget-master', 'Mjeshtër buxheti', 'Mbaj përdorimin e buxhetit nën 80% për 3 muaj.', '3 muaj nën 80%', FALSE, NULL),
                    ('marathoner', 'Maratonist', 'Regjistro 100 km aktiv drejt objektivit të fitnessit.', '100 km të regjistruara', TRUE, 100)
                ON CONFLICT (slug) DO NOTHING;
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS employee_gamification (
                    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    level INTEGER NOT NULL DEFAULT 1,
                    xp INTEGER NOT NULL DEFAULT 0,
                    points INTEGER NOT NULL DEFAULT 0,
                    streak_days INTEGER NOT NULL DEFAULT 0,
                    class_label VARCHAR(100) NOT NULL DEFAULT 'I ri',
                    marathoner_miles INTEGER NOT NULL DEFAULT 0,
                    last_active_date DATE,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS journey_progress (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    category VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'completed',
                    completed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, category)
                );
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS quiz_scores (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    category VARCHAR(50) NOT NULL,
                    score INTEGER NOT NULL,
                    total INTEGER NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, category)
                );
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS employee_achievements (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    achievement_slug VARCHAR(50) NOT NULL REFERENCES achievements(slug) ON DELETE CASCADE,
                    unlocked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, achievement_slug)
                );
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS employee_reviews (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    perk_id UUID NOT NULL REFERENCES perks(id) ON DELETE CASCADE,
                    rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    feedback TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, perk_id)
                );
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
