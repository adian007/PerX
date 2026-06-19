"""Plan optimization orchestration (ADR-004)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import InteractionType, ProviderStatus
from app.models.perk import Perk, PerkInteraction
from app.models.user import User
from app.repositories.budget import get_current_allocation, increment_pending_cents
from app.repositories.optimizer import create_optimizer_run, get_optimizer_run_for_employee
from app.repositories.perk import get_perk_with_provider
from app.repositories.selection import (
    create_selection,
    has_pending_or_approved_selection,
)
from app.schemas.optimizer import (
    ConfirmPlanResponseData,
    OptimizePlanApprovedPerk,
    OptimizePlanResponseData,
)
from app.services.access_control import require_employee_profile
from app.services.budget import (
    InsufficientBudgetError,
    atomic_decrement_budget,
    ensure_budget_cached,
    rollback_budget_decrement,
)
from app.services.optimizer.knapsack import solve_knapsack
from app.services.recommendation.cold_start import score_cold_start_recommendations
from app.services.recommendation.engine import affinity_for_employee
from app.services.recommendation.hybrid import compute_warm_recommendations
from app.services.recommendation.mappers import employee_from_orm, perk_from_orm, ucb_counts_from_interactions
from app.services.recommendation.mode import mode_for_employee
from app.utils.formatting import format_money
from app.utils.redis import RedisClient


def _format_money(cents: int, currency_code: str, locale: str) -> str:
    return format_money(cents, currency_code=currency_code, locale=locale)


async def _score_perks(
    db: AsyncSession,
    profile,
    perks: list[Perk],
    budget_cents: int,
) -> dict[uuid.UUID, float]:
    """Score perks via recommendation engine or popularity/quality fallback."""

    rec_perks = [perk_from_orm(perk) for perk in perks]
    employee = employee_from_orm(profile)
    affinity = affinity_for_employee(profile)
    mode = mode_for_employee(employee)

    interactions = await db.scalars(
        select(PerkInteraction).where(PerkInteraction.employee_id == profile.id)
    )
    ucb_counts = ucb_counts_from_interactions(
        [
            {
                "perk_id": str(row.perk_id),
                "recommendation_rank": row.recommendation_rank,
            }
            for row in interactions
        ]
    )

    if mode == "warm":
        scored = compute_warm_recommendations(
            affinity_vector=affinity,
            available_perks=rec_perks,
            budget_remaining_cents=budget_cents,
            ucb_counts=ucb_counts,
            limit=len(rec_perks),
        )
    else:
        scored = score_cold_start_recommendations(
            affinity_vector=affinity,
            available_perks=rec_perks,
            budget_remaining_cents=budget_cents,
            limit=len(rec_perks),
        )

    score_map = {uuid.UUID(item.perk.id): float(item.recommendation_score) for item in scored}

    for perk in perks:
        if perk.id not in score_map:
            quality = float(perk.quality_score or 0.5)
            popularity = float(perk.popularity_score or 0.0)
            score_map[perk.id] = round(0.6 * quality + 0.4 * popularity, 6)

    return score_map


async def _load_valid_perks(
    db: AsyncSession,
    perk_ids: list[uuid.UUID],
) -> list[Perk]:
    """Load active perks from approved providers."""

    perks: list[Perk] = []
    for perk_id in perk_ids:
        perk = await get_perk_with_provider(db, perk_id)
        if (
            perk is None
            or not perk.is_active
            or perk.provider.status != ProviderStatus.active
        ):
            continue
        perks.append(perk)
    return perks


async def optimize_plan(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    *,
    perk_ids: list[uuid.UUID],
) -> OptimizePlanResponseData:
    """Run knapsack optimization over submitted perk ids."""

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

    if not perk_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "At least one perk_id is required",
                "details": {},
            },
        )

    perks = await _load_valid_perks(db, perk_ids)
    if not perks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERK_NOT_FOUND",
                "message": "No valid perks found for optimization",
                "details": {},
            },
        )

    budget_available = await ensure_budget_cached(redis, allocation)
    score_map = await _score_perks(db, profile, perks, budget_available)

    knapsack_items = [
        {
            "id": perk.id,
            "price_cents": perk.employee_price_cents,
            "score": score_map[perk.id],
            "name": perk.name,
        }
        for perk in perks
    ]

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: solve_knapsack(knapsack_items, budget_available),
    )

    approved_set = set(result["approved_ids"])
    approved_perks: list[OptimizePlanApprovedPerk] = []
    for item in knapsack_items:
        included = item["id"] in approved_set
        exclusion_reason = None
        if not included:
            over = item["price_cents"] - budget_available
            if over > 0:
                exclusion_reason = (
                    f"Would exceed budget by {_format_money(over, allocation.currency_code, user.locale)}"
                )
            else:
                exclusion_reason = "Lower priority within budget constraint"
        approved_perks.append(
            OptimizePlanApprovedPerk(
                perk_id=item["id"],
                name=item["name"],
                price_cents=item["price_cents"],
                score=item["score"],
                included=included,
                exclusion_reason=exclusion_reason,
            )
        )

    included_count = len(result["approved_ids"])
    explanation = (
        f"We selected {included_count} of {len(perks)} perks to maximize your benefit "
        f"within the {_format_money(budget_available, allocation.currency_code, user.locale)} budget."
    )

    wishlist_scores = {str(perk_id): score_map[perk_id] for perk_id in score_map}

    run = await create_optimizer_run(
        db,
        employee_id=profile.id,
        wishlist_perk_ids=[p.id for p in perks],
        wishlist_scores=wishlist_scores,
        budget_available_cents=budget_available,
        approved_perk_ids=result["approved_ids"],
        excluded_perk_ids=result["excluded_ids"],
        total_cost_cents=result["total_cost_cents"],
        total_score=result["total_score"],
        solver_status=result["status"],
        solver_time_ms=result["solver_time_ms"],
    )

    return OptimizePlanResponseData(
        run_id=str(run.id),
        status=result["status"],
        solver_time_ms=result["solver_time_ms"],
        budget_available_cents=budget_available,
        approved_perks=approved_perks,
        total_cost_cents=result["total_cost_cents"],
        total_score=float(result["total_score"]),
        explanation=explanation,
    )


async def confirm_optimized_plan(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    *,
    run_id: uuid.UUID,
) -> ConfirmPlanResponseData:
    """Create selections for an optimizer run's approved perks."""

    profile = await require_employee_profile(db, user)
    run = await get_optimizer_run_for_employee(
        db, run_id=run_id, employee_id=profile.id
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RUN_NOT_FOUND",
                "message": "Optimizer run not found",
                "details": {},
            },
        )

    if not run.approved_perk_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_APPROVED_PERKS",
                "message": "Optimizer run has no approved perks to confirm",
                "details": {},
            },
        )

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

    approved_ids = list(run.approved_perk_ids)
    perks_result = await db.scalars(
        select(Perk)
        .options(selectinload(Perk.provider))
        .where(Perk.id.in_(approved_ids))
    )
    perks_by_id = {perk.id: perk for perk in perks_result.all()}

    total_cost = sum(
        perks_by_id[pid].employee_price_cents
        for pid in approved_ids
        if pid in perks_by_id
    )

    try:
        remaining = await atomic_decrement_budget(redis, allocation, total_cost)
    except InsufficientBudgetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INSUFFICIENT_BUDGET",
                "message": "Not enough budget remaining to confirm this plan",
                "details": {},
            },
        ) from exc

    selection_ids: list[str] = []
    try:
        for perk_id in approved_ids:
            perk = perks_by_id.get(perk_id)
            if perk is None:
                continue

            if perk.currency_code != allocation.currency_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "CURRENCY_MISMATCH",
                        "message": "Perk currency does not match employer default",
                        "details": {"perk_id": str(perk_id)},
                    },
                )

            if await has_pending_or_approved_selection(
                db, employee_id=profile.id, perk_id=perk.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ALREADY_SELECTED_THIS_MONTH",
                        "message": "You already have an active selection for a perk in this plan",
                        "details": {"perk_id": str(perk_id)},
                    },
                )

            selection = await create_selection(
                db,
                employee_id=profile.id,
                perk_id=perk.id,
                employer_id=profile.employer_id,
                budget_allocation_id=allocation.id,
                price_cents_snapshot=perk.employee_price_cents,
                currency_code=perk.currency_code,
            )
            await increment_pending_cents(db, allocation.id, perk.employee_price_cents)
            db.add(
                PerkInteraction(
                    employee_id=profile.id,
                    perk_id=perk.id,
                    interaction_type=InteractionType.select,
                )
            )
            selection_ids.append(str(selection.id))

        await db.flush()
    except Exception:
        await rollback_budget_decrement(redis, allocation, total_cost)
        raise

    return ConfirmPlanResponseData(
        selection_ids=selection_ids,
        budget_remaining_cents=remaining,
        budget_remaining_formatted=_format_money(remaining, allocation.currency_code, user.locale),
    )
