"""Perk selection routes — quick-add, optimize-plan, and employee selection list."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.optimizer import (
    ConfirmPlanRequest,
    ConfirmPlanResponseData,
    OptimizePlanRequest,
    OptimizePlanResponseData,
)
from app.schemas.recommendations import ApiEnvelope
from app.schemas.selections import QuickAddRequest, QuickAddResponseData
from app.services.optimizer.plan import confirm_optimized_plan, optimize_plan
from app.services.selections import cancel_selection, get_my_selections, quick_add_selection
from app.utils.envelope import envelope
from app.utils.redis import RedisClient, get_redis

router = APIRouter(tags=["selections"])


@router.post("/selections/quick-add", response_model=ApiEnvelope)
async def quick_add(
    body: QuickAddRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Add a single perk immediately (fast path with Redis atomic budget check)."""

    data = await quick_add_selection(
        db,
        redis,
        current_user,
        perk_id=body.perk_id,
    )
    return envelope(QuickAddResponseData.model_validate(data.model_dump()).model_dump())


@router.get("/me/selections", response_model=ApiEnvelope)
async def my_selections(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
    status: str | None = Query(default=None),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """List perk selections for the authenticated employee."""

    items = await get_my_selections(db, current_user, status_filter=status, limit=limit)
    payload = [item.model_dump() for item in items]
    response = envelope(payload)
    response["meta"].update(
        {"total": len(payload), "page": 1, "per_page": limit, "pages": 1}
    )
    return response


@router.post("/selections/optimize-plan", response_model=ApiEnvelope)
async def optimize_plan_route(
    body: OptimizePlanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Submit perks for knapsack budget optimization."""

    data = await optimize_plan(db, redis, current_user, perk_ids=body.perk_ids)
    return envelope(OptimizePlanResponseData.model_validate(data.model_dump()).model_dump())


@router.post(
    "/selections/optimize-plan/{run_id}/confirm",
    response_model=ApiEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_optimize_plan(
    run_id: uuid.UUID,
    body: ConfirmPlanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Confirm and create selections from an optimizer run."""

    data = await confirm_optimized_plan(db, redis, current_user, run_id=run_id)
    return envelope(ConfirmPlanResponseData.model_validate(data.model_dump()).model_dump())


@router.delete("/selections/{selection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_pending_selection(
    selection_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> None:
    """Cancel a pending selection before employer approval."""

    await cancel_selection(db, redis, current_user, selection_id)
