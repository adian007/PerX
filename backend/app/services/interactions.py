"""Perk interaction logging business logic."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InteractionType
from app.models.perk import PerkInteraction
from app.models.user import User
from app.repositories.interaction import create_interaction, create_interactions_batch
from app.repositories.perk import get_perk_with_provider
from app.schemas.interactions import (
    InteractionBatchResponse,
    InteractionCreateRequest,
    InteractionLoggedResponse,
)
from app.services.access_control import require_employee_profile


def _to_interaction_row(
    employee_id,
    event: InteractionCreateRequest,
    *,
    is_offline: bool = False,
) -> PerkInteraction:
    occurred = event.occurred_at
    if occurred is not None and occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)

    return PerkInteraction(
        employee_id=employee_id,
        perk_id=event.perk_id,
        interaction_type=InteractionType(event.interaction_type),
        recommendation_rank=event.recommendation_rank,
        page_context=event.page_context,
        session_id=event.session_id,
        is_offline=is_offline,
        occurred_at=occurred or datetime.now(timezone.utc),
    )


async def log_interaction(
    db: AsyncSession,
    user: User,
    *,
    event: InteractionCreateRequest,
) -> InteractionLoggedResponse:
    """Log a single employee interaction."""

    profile = await require_employee_profile(db, user)
    perk = await get_perk_with_provider(db, event.perk_id)
    if perk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERK_NOT_FOUND",
                "message": "Perk not found",
                "details": {},
            },
        )

    await create_interaction(
        db,
        employee_id=profile.id,
        perk_id=event.perk_id,
        interaction_type=InteractionType(event.interaction_type),
        recommendation_rank=event.recommendation_rank,
        page_context=event.page_context,
        session_id=event.session_id,
        occurred_at=event.occurred_at,
        is_offline=event.occurred_at is not None,
    )
    return InteractionLoggedResponse()


async def log_interactions_batch(
    db: AsyncSession,
    user: User,
    *,
    events: list[InteractionCreateRequest],
) -> InteractionBatchResponse:
    """Log multiple interactions; skip invalid perk references."""

    profile = await require_employee_profile(db, user)
    accepted_rows: list[PerkInteraction] = []
    rejected = 0

    for event in events:
        perk = await get_perk_with_provider(db, event.perk_id)
        if perk is None:
            rejected += 1
            continue
        accepted_rows.append(
            _to_interaction_row(profile.id, event, is_offline=event.occurred_at is not None)
        )

    if accepted_rows:
        await create_interactions_batch(db, accepted_rows)

    return InteractionBatchResponse(accepted=len(accepted_rows), rejected=rejected)
