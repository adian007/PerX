"""Optimizer run persistence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.optimizer import OptimizerRun


async def create_optimizer_run(
    db: AsyncSession,
    *,
    employee_id: uuid.UUID,
    wishlist_perk_ids: list[uuid.UUID],
    wishlist_scores: dict[str, Any],
    budget_available_cents: int,
    approved_perk_ids: list[uuid.UUID] | None,
    excluded_perk_ids: list[uuid.UUID] | None,
    total_cost_cents: int | None,
    total_score: float | None,
    solver_status: str | None,
    solver_time_ms: int | None,
) -> OptimizerRun:
    """Persist an optimizer audit row."""

    run = OptimizerRun(
        employee_id=employee_id,
        wishlist_perk_ids=wishlist_perk_ids,
        wishlist_scores=wishlist_scores,
        budget_available_cents=budget_available_cents,
        approved_perk_ids=approved_perk_ids,
        excluded_perk_ids=excluded_perk_ids,
        total_cost_cents=total_cost_cents,
        total_score=total_score,
        solver_status=solver_status,
        solver_time_ms=solver_time_ms,
    )
    db.add(run)
    await db.flush()
    return run


async def get_optimizer_run_for_employee(
    db: AsyncSession,
    *,
    run_id: uuid.UUID,
    employee_id: uuid.UUID,
) -> OptimizerRun | None:
    """Load an optimizer run scoped to the employee."""

    return await db.scalar(
        select(OptimizerRun).where(
            OptimizerRun.id == run_id,
            OptimizerRun.employee_id == employee_id,
        )
    )
