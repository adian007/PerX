"""Interaction logging routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.interactions import (
    InteractionBatchRequest,
    InteractionBatchResponse,
    InteractionCreateRequest,
    InteractionLoggedResponse,
)
from app.schemas.recommendations import ApiEnvelope
from app.services.interactions import log_interaction, log_interactions_batch
from app.utils.envelope import envelope

router = APIRouter(tags=["interactions"])


@router.post(
    "/interactions",
    response_model=ApiEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_interaction(
    body: InteractionCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Log a single perk interaction."""

    data = await log_interaction(db, current_user, event=body)
    return envelope(InteractionLoggedResponse.model_validate(data.model_dump()).model_dump())


@router.post(
    "/interactions/batch",
    response_model=ApiEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_interactions_batch(
    body: InteractionBatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Log a batch of perk interactions (offline replay)."""

    data = await log_interactions_batch(db, current_user, events=body.events)
    return envelope(InteractionBatchResponse.model_validate(data.model_dump()).model_dump())
