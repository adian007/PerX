"""Package catalog repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.package import Package, PackageItem
from app.models.perk import Perk


async def list_active_curated_packages(
    db: AsyncSession,
    *,
    limit: int = 50,
) -> list[Package]:
    """Return active curated packages with items and perks loaded."""

    result = await db.scalars(
        select(Package)
        .options(
            selectinload(Package.items).selectinload(PackageItem.perk).selectinload(Perk.provider)
        )
        .where(Package.is_active.is_(True), Package.is_curated.is_(True))
        .order_by(Package.name)
        .limit(limit)
    )
    return list(result.all())


async def get_active_package_with_items(
    db: AsyncSession,
    package_id: uuid.UUID,
) -> Package | None:
    """Load an active package with items and perks."""

    return await db.scalar(
        select(Package)
        .options(
            selectinload(Package.items).selectinload(PackageItem.perk).selectinload(Perk.provider)
        )
        .where(Package.id == package_id, Package.is_active.is_(True))
    )
