"""Provider profile repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import ProviderProfile


async def get_provider_by_user_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> ProviderProfile | None:
    """Load provider profile for an auth user."""

    return await db.scalar(
        select(ProviderProfile).where(ProviderProfile.user_id == user_id)
    )
