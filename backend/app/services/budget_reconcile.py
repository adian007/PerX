"""Budget cache reconciliation — Postgres remaining_cents is source of truth (ADR-006)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.budget import BudgetAllocation
from app.repositories.budget import current_period
from app.services.budget import budget_cache_key, ttl_seconds_for_period
from app.utils.redis import RedisClient, get_redis_client

logger = logging.getLogger(__name__)

RECONCILE_INTERVAL_SECONDS = 300


async def reconcile_budget_cache(db: AsyncSession, redis: RedisClient) -> int:
    """Refresh Redis budget keys from Postgres remaining_cents for the current period."""

    year, month = current_period()
    allocations = (
        await db.scalars(
            select(BudgetAllocation).where(
                BudgetAllocation.period_year == year,
                BudgetAllocation.period_month == month,
            )
        )
    ).all()

    updated = 0
    for allocation in allocations:
        key = budget_cache_key(
            allocation.employer_id,
            allocation.employee_id,
            period_year=allocation.period_year,
            period_month=allocation.period_month,
        )
        ttl = ttl_seconds_for_period(allocation.period_year, allocation.period_month)
        await redis.setex(key, ttl, str(allocation.remaining_cents))
        updated += 1

    return updated


async def run_reconcile_loop(interval_seconds: int = RECONCILE_INTERVAL_SECONDS) -> None:
    """Background loop that reconciles budget cache every interval until cancelled."""

    while True:
        try:
            redis = await get_redis_client()
            async with AsyncSessionLocal() as db:
                count = await reconcile_budget_cache(db, redis)
            logger.debug("Budget reconcile refreshed %s allocation key(s)", count)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — loop must survive transient failures
            logger.warning("Budget reconcile failed: %s", exc)

        await asyncio.sleep(interval_seconds)
