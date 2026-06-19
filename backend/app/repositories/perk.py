"""Perk catalog repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ProviderStatus
from app.models.perk import Perk
from app.models.provider import ProviderProfile


async def get_perk_with_provider(
    db: AsyncSession,
    perk_id: uuid.UUID,
) -> Perk | None:
    """Load a perk with its provider relationship."""

    return await db.scalar(
        select(Perk)
        .options(selectinload(Perk.provider))
        .where(Perk.id == perk_id)
    )


async def list_catalog_perks(
    db: AsyncSession,
    *,
    category: str | None = None,
    limit: int = 100,
) -> list[Perk]:
    """Return active perks from approved providers for the employee catalog."""

    stmt = (
        select(Perk)
        .join(ProviderProfile, Perk.provider_id == ProviderProfile.id)
        .options(selectinload(Perk.provider))
        .where(
            Perk.is_active.is_(True),
            ProviderProfile.status == ProviderStatus.active,
        )
        .order_by(Perk.popularity_score.desc().nullslast())
        .limit(limit)
    )
    if category is not None:
        stmt = stmt.where(Perk.category == category)

    result = await db.scalars(stmt)
    return list(result.all())


async def list_provider_perks(
    db: AsyncSession,
    provider_id: uuid.UUID,
) -> list[Perk]:
    """Return all perks owned by a provider."""

    result = await db.scalars(
        select(Perk)
        .options(selectinload(Perk.provider))
        .where(Perk.provider_id == provider_id)
        .order_by(Perk.created_at.desc())
    )
    return list(result.all())
