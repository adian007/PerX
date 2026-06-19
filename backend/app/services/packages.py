"""Curated package catalog and package selection."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InteractionType, ProviderStatus
from app.models.perk import PerkInteraction
from app.models.user import User
from app.repositories.budget import get_current_allocation, increment_pending_cents
from app.repositories.package import get_active_package_with_items, list_active_curated_packages
from app.repositories.selection import create_selection, has_pending_or_approved_selection
from app.schemas.packages import PackageListItem, PackagePerkItem, PackageSelectionResponseData
from app.services.access_control import require_employee_profile
from app.services.budget import InsufficientBudgetError, atomic_decrement_budget, rollback_budget_decrement
from app.utils.redis import RedisClient


async def list_packages_for_employees(db: AsyncSession) -> list[PackageListItem]:
    """Return active curated packages without provider cost fields."""

    packages = await list_active_curated_packages(db)
    result: list[PackageListItem] = []
    for package in packages:
        items: list[PackagePerkItem] = []
        for item in package.items:
            perk = item.perk
            if not perk.is_active or perk.provider.status != ProviderStatus.active:
                continue
            items.append(
                PackagePerkItem(
                    perk_id=str(perk.id),
                    name=perk.name,
                    category=perk.category.value if hasattr(perk.category, "value") else str(perk.category),
                    employee_price_cents=perk.employee_price_cents,
                    provider_name=perk.provider.company_name,
                )
            )
        if not items:
            continue
        result.append(
            PackageListItem(
                id=str(package.id),
                name=package.name,
                description=package.description,
                category=package.category,
                total_price_cents=package.total_price_cents,
                currency_code=package.currency_code,
                items=items,
            )
        )
    return result


async def select_package(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    package_id: uuid.UUID,
) -> PackageSelectionResponseData:
    """Create pending selections for every perk in a package."""

    profile = await require_employee_profile(db, user)
    allocation = await get_current_allocation(db, profile.id)
    if allocation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BUDGET_PERIOD_CLOSED",
                "message": "No budget allocation for the current period",
                "details": {},
            },
        )

    package = await get_active_package_with_items(db, package_id)
    if package is None or not package.is_curated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PACKAGE_NOT_FOUND",
                "message": "Package not found or unavailable",
                "details": {},
            },
        )

    if package.currency_code != allocation.currency_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CURRENCY_MISMATCH",
                "message": "Package currency does not match employer default",
                "details": {},
            },
        )

    active_items = [
        item
        for item in package.items
        if item.perk.is_active and item.perk.provider.status == ProviderStatus.active
    ]
    if not active_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PACKAGE_NOT_FOUND",
                "message": "Package has no available perks",
                "details": {},
            },
        )

    total_price = sum(item.perk.employee_price_cents * item.quantity for item in active_items)
    if total_price != package.total_price_cents:
        total_price = package.total_price_cents

    for item in active_items:
        if await has_pending_or_approved_selection(
            db, employee_id=profile.id, perk_id=item.perk.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "ALREADY_SELECTED_THIS_MONTH",
                    "message": "You already have an active selection for a perk in this package",
                    "details": {"perk_id": str(item.perk.id)},
                },
            )

    try:
        remaining = await atomic_decrement_budget(redis, allocation, total_price)
    except InsufficientBudgetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INSUFFICIENT_BUDGET",
                "message": "Not enough budget remaining for this package",
                "details": {},
            },
        ) from exc

    selection_ids: list[str] = []
    try:
        for item in active_items:
            perk = item.perk
            selection = await create_selection(
                db,
                employee_id=profile.id,
                perk_id=perk.id,
                employer_id=profile.employer_id,
                budget_allocation_id=allocation.id,
                price_cents_snapshot=perk.employee_price_cents * item.quantity,
                currency_code=perk.currency_code,
                package_id=package.id,
            )
            selection_ids.append(str(selection.id))
            db.add(
                PerkInteraction(
                    employee_id=profile.id,
                    perk_id=perk.id,
                    interaction_type=InteractionType.select,
                )
            )
        await increment_pending_cents(db, allocation.id, total_price)
        await db.flush()
    except Exception:
        await rollback_budget_decrement(redis, allocation, total_price)
        raise

    return PackageSelectionResponseData(
        package_id=str(package.id),
        selection_ids=selection_ids,
        status="pending_approval",
        total_price_cents=total_price,
        budget_remaining_cents=remaining,
        message="Your package selection is awaiting approval.",
    )
