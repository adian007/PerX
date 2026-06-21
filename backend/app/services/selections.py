"""Perk selection business logic — quick-add path (ADR-004)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InteractionType, ProviderStatus, SelectionStatus
from app.models.perk import PerkInteraction
from app.models.user import User
from app.repositories.budget import decrement_pending_cents, get_current_allocation, increment_pending_cents
from app.repositories.perk import get_perk_with_provider
from app.repositories.selection import (
    create_selection,
    get_employee_selection,
    has_pending_or_approved_selection,
    list_employee_selections,
    set_selection_cancelled,
)
from app.schemas.selections import QuickAddResponseData, SelectionListItem
from app.services.access_control import require_employee_profile
from app.services.budget import (
    InsufficientBudgetError,
    atomic_decrement_budget,
    rollback_budget_decrement,
)
from app.services.gamification import award_quick_add
from app.services.perks import perk_for_employee
from app.utils.formatting import format_money
from app.utils.redis import RedisClient


async def quick_add_selection(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    *,
    perk_id: uuid.UUID,
) -> QuickAddResponseData:
    """Fast-path single perk selection with atomic Redis budget check."""

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

    perk = await get_perk_with_provider(db, perk_id)
    if perk is None or not perk.is_active or perk.provider.status != ProviderStatus.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERK_NOT_FOUND",
                "message": "Perk not found or unavailable",
                "details": {},
            },
        )

    if perk.currency_code != allocation.currency_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CURRENCY_MISMATCH",
                "message": "Perk currency does not match employer default",
                "details": {},
            },
        )

    if await has_pending_or_approved_selection(db, employee_id=profile.id, perk_id=perk.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_SELECTED_THIS_MONTH",
                "message": "You already have an active selection for this perk",
                "details": {},
            },
        )

    price = perk.employee_price_cents
    try:
        remaining = await atomic_decrement_budget(redis, allocation, price)
    except InsufficientBudgetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INSUFFICIENT_BUDGET",
                "message": "Not enough budget remaining for this perk",
                "details": {},
            },
        ) from exc

    try:
        selection = await create_selection(
            db,
            employee_id=profile.id,
            perk_id=perk.id,
            employer_id=profile.employer_id,
            budget_allocation_id=allocation.id,
            price_cents_snapshot=price,
            currency_code=perk.currency_code,
        )
        await increment_pending_cents(db, allocation.id, price)
        db.add(
            PerkInteraction(
                employee_id=profile.id,
                perk_id=perk.id,
                interaction_type=InteractionType.select,
            )
        )
        await db.flush()
    except Exception:
        await rollback_budget_decrement(redis, allocation, price)
        raise

    await award_quick_add(db, user, category=perk.category.value)

    formatted = format_money(
        remaining,
        currency_code=perk.currency_code,
        locale=user.locale,
    )
    return QuickAddResponseData(
        selection_id=str(selection.id),
        status=selection.status.value,
        budget_remaining_cents=remaining,
        budget_remaining_formatted=formatted,
        message="Your selection is awaiting approval.",
    )


async def get_my_selections(
    db: AsyncSession,
    user: User,
    *,
    status_filter: str | None = None,
    limit: int = 20,
) -> list[SelectionListItem]:
    """List current employee selections."""

    profile = await require_employee_profile(db, user)
    from app.models.enums import SelectionStatus

    status_enum = SelectionStatus(status_filter) if status_filter else None
    rows = await list_employee_selections(
        db, profile.id, status=status_enum, limit=limit
    )
    return [
        SelectionListItem(
            id=str(row.id),
            status=row.status.value,
            price_cents_snapshot=row.price_cents_snapshot,
            selected_at=row.selected_at.isoformat(),
            perk=perk_for_employee(row.perk).model_dump(mode="json"),
        )
        for row in rows
    ]


async def cancel_selection(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    selection_id: uuid.UUID,
) -> None:
    """Cancel a pending selection and roll back budget reservations."""

    profile = await require_employee_profile(db, user)
    selection = await get_employee_selection(db, selection_id, profile.id)
    if selection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SELECTION_NOT_FOUND",
                "message": "Selection not found",
                "details": {},
            },
        )

    if selection.status != SelectionStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SELECTION_NOT_CANCELLABLE",
                "message": "Only pending selections can be cancelled",
                "details": {"status": selection.status.value},
            },
        )

    allocation = selection.budget_allocation
    price = selection.price_cents_snapshot
    await decrement_pending_cents(db, allocation.id, price)
    await rollback_budget_decrement(redis, allocation, price)
    await set_selection_cancelled(db, selection)
