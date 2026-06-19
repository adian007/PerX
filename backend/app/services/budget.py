"""Budget cache and atomic decrement (Redis Lua + Postgres source of truth)."""

from __future__ import annotations

import calendar
import uuid
from datetime import datetime, timezone

from app.models.budget import BudgetAllocation
from app.utils.redis import RedisClient


class InsufficientBudgetError(Exception):
    """Raised when Redis atomic decrement finds insufficient remaining budget."""


def budget_cache_key(
    employer_id: uuid.UUID,
    employee_id: uuid.UUID,
    *,
    period_year: int,
    period_month: int,
) -> str:
    """Redis key for remaining budget cents (ADR-006)."""

    return f"budget:{employer_id}:{employee_id}:{period_year:04d}-{period_month:02d}"


def ttl_seconds_for_period(period_year: int, period_month: int) -> int:
    """TTL until end of budget month plus one day."""

    last_day = calendar.monthrange(period_year, period_month)[1]
    period_end = datetime(period_year, period_month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    remaining = int((period_end - now).total_seconds()) + 86400
    return max(remaining, 3600)


async def ensure_budget_cached(
    redis: RedisClient,
    allocation: BudgetAllocation,
) -> int:
    """Load remaining cents into Redis if missing; always trust Postgres on init."""

    key = budget_cache_key(
        allocation.employer_id,
        allocation.employee_id,
        period_year=allocation.period_year,
        period_month=allocation.period_month,
    )
    cached = await redis.get(key)
    if cached is not None:
        return int(cached)

    remaining = allocation.remaining_cents
    ttl = ttl_seconds_for_period(allocation.period_year, allocation.period_month)
    await redis.setex(key, ttl, str(remaining))
    return remaining


async def atomic_decrement_budget(
    redis: RedisClient,
    allocation: BudgetAllocation,
    amount_cents: int,
) -> int:
    """Decrement cached budget atomically; raises InsufficientBudgetError on failure."""

    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")

    await ensure_budget_cached(redis, allocation)
    key = budget_cache_key(
        allocation.employer_id,
        allocation.employee_id,
        period_year=allocation.period_year,
        period_month=allocation.period_month,
    )
    new_balance = await redis.eval_budget_decr(key, amount_cents)
    if new_balance < 0:
        raise InsufficientBudgetError("Insufficient budget")
    return new_balance


async def rollback_budget_decrement(
    redis: RedisClient,
    allocation: BudgetAllocation,
    amount_cents: int,
) -> int:
    """Restore budget in Redis after a failed Postgres write."""

    key = budget_cache_key(
        allocation.employer_id,
        allocation.employee_id,
        period_year=allocation.period_year,
        period_month=allocation.period_month,
    )
    return await redis.incrby(key, amount_cents)
