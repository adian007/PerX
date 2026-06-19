"""Employee wishlist business logic."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InteractionType, ProviderStatus
from app.models.perk import PerkInteraction
from app.models.user import User
from app.repositories.perk import get_perk_with_provider
from app.repositories.wishlist import (
    add_wishlist_item,
    has_wishlist_item,
    list_wishlist_items,
    remove_wishlist_item,
)
from app.schemas.wishlist import WishlistAddResponseData
from app.services.access_control import require_employee_profile
from app.services.perks import perk_for_employee


async def get_my_wishlist(db: AsyncSession, user: User) -> list[dict]:
    """Return employee-safe perk payloads for wishlist items."""

    profile = await require_employee_profile(db, user)
    items = await list_wishlist_items(db, profile.id)
    return [perk_for_employee(item.perk).model_dump(mode="json") for item in items]


async def add_to_wishlist(
    db: AsyncSession,
    user: User,
    *,
    perk_id: uuid.UUID,
) -> WishlistAddResponseData:
    """Add a perk to the employee wishlist."""

    profile = await require_employee_profile(db, user)
    perk = await get_perk_with_provider(db, perk_id)

    if perk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERK_NOT_FOUND",
                "message": "Perk not found",
                "details": {},
            },
        )

    if not perk.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PERK_INACTIVE",
                "message": "Perk is not currently available",
                "details": {},
            },
        )

    if perk.provider.status != ProviderStatus.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERK_NOT_FOUND",
                "message": "Perk not found or unavailable",
                "details": {},
            },
        )

    if await has_wishlist_item(db, employee_id=profile.id, perk_id=perk.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_IN_WISHLIST",
                "message": "Perk is already on your wishlist",
                "details": {},
            },
        )

    await add_wishlist_item(db, employee_id=profile.id, perk_id=perk.id)
    db.add(
        PerkInteraction(
            employee_id=profile.id,
            perk_id=perk.id,
            interaction_type=InteractionType.add_to_wishlist,
        )
    )
    await db.flush()

    return WishlistAddResponseData(added=True, perk_id=perk.id)


async def remove_from_wishlist(
    db: AsyncSession,
    user: User,
    *,
    perk_id: uuid.UUID,
) -> None:
    """Remove a perk from the employee wishlist."""

    profile = await require_employee_profile(db, user)
    removed = await remove_wishlist_item(db, employee_id=profile.id, perk_id=perk_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERK_NOT_FOUND",
                "message": "Perk not on wishlist",
                "details": {},
            },
        )

    db.add(
        PerkInteraction(
            employee_id=profile.id,
            perk_id=perk_id,
            interaction_type=InteractionType.remove_from_wishlist,
        )
    )
    await db.flush()
