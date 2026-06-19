"""Employee wishlist repository."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import EmployeeWishlist


async def list_wishlist_items(
    db: AsyncSession,
    employee_id: uuid.UUID,
) -> list[EmployeeWishlist]:
    """Return wishlist rows with perks loaded."""

    result = await db.scalars(
        select(EmployeeWishlist)
        .options(selectinload(EmployeeWishlist.perk))
        .where(EmployeeWishlist.employee_id == employee_id)
        .order_by(EmployeeWishlist.added_at.desc())
    )
    return list(result.all())


async def has_wishlist_item(
    db: AsyncSession,
    *,
    employee_id: uuid.UUID,
    perk_id: uuid.UUID,
) -> bool:
    """True if the perk is already on the employee wishlist."""

    existing = await db.scalar(
        select(EmployeeWishlist.id).where(
            EmployeeWishlist.employee_id == employee_id,
            EmployeeWishlist.perk_id == perk_id,
        )
    )
    return existing is not None


async def add_wishlist_item(
    db: AsyncSession,
    *,
    employee_id: uuid.UUID,
    perk_id: uuid.UUID,
) -> EmployeeWishlist:
    """Insert a wishlist row."""

    item = EmployeeWishlist(employee_id=employee_id, perk_id=perk_id)
    db.add(item)
    await db.flush()
    return item


async def remove_wishlist_item(
    db: AsyncSession,
    *,
    employee_id: uuid.UUID,
    perk_id: uuid.UUID,
) -> bool:
    """Delete a wishlist row; returns True if a row was removed."""

    result = await db.execute(
        delete(EmployeeWishlist).where(
            EmployeeWishlist.employee_id == employee_id,
            EmployeeWishlist.perk_id == perk_id,
        )
    )
    return result.rowcount > 0
