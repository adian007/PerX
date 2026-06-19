"""Budget allocation repository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import BudgetAllocation


def current_period() -> tuple[int, int]:
    """Return (year, month) for the current UTC budget period."""

    now = datetime.now(timezone.utc)
    return now.year, now.month


async def get_current_allocation(
    db: AsyncSession,
    employee_id: uuid.UUID,
) -> BudgetAllocation | None:
    """Return the budget allocation for the current UTC month."""

    year, month = current_period()
    return await db.scalar(
        select(BudgetAllocation).where(
            BudgetAllocation.employee_id == employee_id,
            BudgetAllocation.period_year == year,
            BudgetAllocation.period_month == month,
        )
    )


async def increment_pending_cents(
    db: AsyncSession,
    allocation_id: uuid.UUID,
    amount_cents: int,
) -> None:
    """Increase pending_cents on the allocation row."""

    await db.execute(
        update(BudgetAllocation)
        .where(BudgetAllocation.id == allocation_id)
        .values(pending_cents=BudgetAllocation.pending_cents + amount_cents)
    )


async def decrement_pending_cents(
    db: AsyncSession,
    allocation_id: uuid.UUID,
    amount_cents: int,
) -> None:
    """Decrease pending_cents on the allocation row."""

    await db.execute(
        update(BudgetAllocation)
        .where(BudgetAllocation.id == allocation_id)
        .values(pending_cents=BudgetAllocation.pending_cents - amount_cents)
    )


async def approve_budget_move(
    db: AsyncSession,
    allocation_id: uuid.UUID,
    amount_cents: int,
) -> None:
    """Move amount from pending to spent on approval."""

    await db.execute(
        update(BudgetAllocation)
        .where(BudgetAllocation.id == allocation_id)
        .values(
            pending_cents=BudgetAllocation.pending_cents - amount_cents,
            spent_cents=BudgetAllocation.spent_cents + amount_cents,
        )
    )
