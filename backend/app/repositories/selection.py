"""Perk selection repository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import EmployeeProfile
from app.models.enums import SelectionStatus
from app.models.perk import Perk
from app.models.selection import PerkSelection


async def create_selection(
    db: AsyncSession,
    *,
    employee_id: uuid.UUID,
    perk_id: uuid.UUID,
    employer_id: uuid.UUID,
    budget_allocation_id: uuid.UUID,
    price_cents_snapshot: int,
    currency_code: str,
    package_id: uuid.UUID | None = None,
) -> PerkSelection:
    """Insert a pending approval selection."""

    selection = PerkSelection(
        employee_id=employee_id,
        perk_id=perk_id,
        employer_id=employer_id,
        budget_allocation_id=budget_allocation_id,
        package_id=package_id,
        status=SelectionStatus.pending_approval,
        price_cents_snapshot=price_cents_snapshot,
        currency_code=currency_code,
    )
    db.add(selection)
    await db.flush()
    return selection


async def get_selection_by_id(
    db: AsyncSession,
    selection_id: uuid.UUID,
) -> PerkSelection | None:
    """Load a selection with employee, perk, and budget allocation."""

    return await db.scalar(
        select(PerkSelection)
        .options(
            selectinload(PerkSelection.employee).selectinload(EmployeeProfile.user),
            selectinload(PerkSelection.perk),
            selectinload(PerkSelection.budget_allocation),
        )
        .where(PerkSelection.id == selection_id)
    )


async def get_employee_selection(
    db: AsyncSession,
    selection_id: uuid.UUID,
    employee_id: uuid.UUID,
) -> PerkSelection | None:
    """Load a selection owned by the given employee."""

    return await db.scalar(
        select(PerkSelection)
        .options(selectinload(PerkSelection.budget_allocation))
        .where(
            PerkSelection.id == selection_id,
            PerkSelection.employee_id == employee_id,
        )
    )


async def has_pending_or_approved_selection(
    db: AsyncSession,
    *,
    employee_id: uuid.UUID,
    perk_id: uuid.UUID,
) -> bool:
    """True if employee already has a pending or approved selection for this perk."""

    existing = await db.scalar(
        select(PerkSelection.id).where(
            PerkSelection.employee_id == employee_id,
            PerkSelection.perk_id == perk_id,
            PerkSelection.status.in_(
                [SelectionStatus.pending_approval, SelectionStatus.approved]
            ),
        )
    )
    return existing is not None


async def list_employee_selections(
    db: AsyncSession,
    employee_id: uuid.UUID,
    *,
    status: SelectionStatus | None = None,
    limit: int = 20,
) -> list[PerkSelection]:
    """List selections for an employee with perk loaded."""

    stmt = (
        select(PerkSelection)
        .options(selectinload(PerkSelection.perk))
        .where(PerkSelection.employee_id == employee_id)
        .order_by(PerkSelection.selected_at.desc())
        .limit(limit)
    )
    if status is not None:
        stmt = stmt.where(PerkSelection.status == status)

    result = await db.scalars(stmt)
    return list(result.all())


async def list_pending_approvals_for_org(
    db: AsyncSession,
    employer_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[PerkSelection]:
    """Pending approval queue scoped to one employer org."""

    result = await db.scalars(
        select(PerkSelection)
        .options(
            selectinload(PerkSelection.employee),
            selectinload(PerkSelection.perk),
            selectinload(PerkSelection.budget_allocation),
        )
        .where(
            PerkSelection.employer_id == employer_id,
            PerkSelection.status == SelectionStatus.pending_approval,
        )
        .order_by(PerkSelection.selected_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.all())


async def list_package_pending_selections(
    db: AsyncSession,
    *,
    package_id: uuid.UUID,
    employer_id: uuid.UUID,
    employee_id: uuid.UUID,
) -> list[PerkSelection]:
    """All pending selections in a package batch for one employee."""

    result = await db.scalars(
        select(PerkSelection)
        .options(
            selectinload(PerkSelection.perk).selectinload(Perk.provider),
            selectinload(PerkSelection.budget_allocation),
            selectinload(PerkSelection.employee).selectinload(EmployeeProfile.user),
        )
        .where(
            PerkSelection.package_id == package_id,
            PerkSelection.employer_id == employer_id,
            PerkSelection.employee_id == employee_id,
            PerkSelection.status == SelectionStatus.pending_approval,
        )
    )
    return list(result.all())


async def resolve_approval_targets(
    db: AsyncSession,
    selection: PerkSelection,
    employer_id: uuid.UUID,
) -> list[PerkSelection]:
    """Expand a selection to its package batch when package_id is set."""

    if selection.package_id is None:
        return [selection]

    batch = await list_package_pending_selections(
        db,
        package_id=selection.package_id,
        employer_id=employer_id,
        employee_id=selection.employee_id,
    )
    return batch if batch else [selection]


async def set_selection_cancelled(db: AsyncSession, selection: PerkSelection) -> None:
    """Mark a selection cancelled."""

    selection.status = SelectionStatus.cancelled
    await db.flush()


async def set_selection_approved(
    db: AsyncSession,
    selection: PerkSelection,
    *,
    approved_by: uuid.UUID,
) -> None:
    """Mark a selection approved."""

    selection.status = SelectionStatus.approved
    selection.approved_by = approved_by
    selection.approved_at = datetime.now(timezone.utc)
    await db.flush()


async def set_selection_rejected(
    db: AsyncSession,
    selection: PerkSelection,
    *,
    reason: str,
) -> None:
    """Mark a selection rejected."""

    selection.status = SelectionStatus.rejected
    selection.rejection_reason = reason
    await db.flush()
