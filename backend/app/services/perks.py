"""Perk catalog and role-aware serialization."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProviderStatus, UserRole
from app.models.perk import Perk
from app.models.user import User
from app.repositories.perk import get_perk_with_provider, list_catalog_perks
from app.repositories.provider import get_provider_by_user_id
from app.schemas.perks import PerkEmployeeRead, PerkProviderRead
from app.services.access_control import assert_provider_owns_perk, assert_role


def perk_for_employee(perk: Perk) -> PerkEmployeeRead:
    """Serialize a perk for employee-facing responses."""

    return PerkEmployeeRead.model_validate(perk)


def perk_for_provider(perk: Perk, user: User) -> PerkProviderRead:
    """Serialize a perk for provider/admin responses after role check."""

    assert_role(user, {UserRole.provider, UserRole.admin})
    return PerkProviderRead.model_validate(perk)


async def browse_catalog(
    db: AsyncSession,
    *,
    category: str | None = None,
    limit: int = 20,
) -> list[PerkEmployeeRead]:
    """Return employee-safe perk rows from the approved-provider catalog."""

    perks = await list_catalog_perks(db, category=category, limit=limit)
    return [perk_for_employee(perk) for perk in perks]


async def get_perk_for_user(
    db: AsyncSession,
    user: User,
    perk_id: uuid.UUID,
) -> dict:
    """Return a single perk with fields scoped to the caller's role."""

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

    if user.role == UserRole.employee:
        if not perk.is_active or perk.provider.status != ProviderStatus.active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "PERK_NOT_FOUND",
                    "message": "Perk not found",
                    "details": {},
                },
            )
        return perk_for_employee(perk).model_dump(mode="json")

    if user.role == UserRole.provider:
        provider = await get_provider_by_user_id(db, user.id)
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": "Provider profile not found",
                    "details": {},
                },
            )
        assert_provider_owns_perk(user, provider, perk)
        return perk_for_provider(perk, user).model_dump(mode="json")

    if user.role == UserRole.admin:
        return perk_for_provider(perk, user).model_dump(mode="json")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "FORBIDDEN",
            "message": "Insufficient role for this operation",
            "details": {},
        },
    )
