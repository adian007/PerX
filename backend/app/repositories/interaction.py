"""Perk interaction repository — append-only inserts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InteractionType
from app.models.perk import PerkInteraction


async def create_interaction(
    db: AsyncSession,
    *,
    employee_id: uuid.UUID,
    perk_id: uuid.UUID,
    interaction_type: InteractionType,
    recommendation_rank: int | None = None,
    page_context: str | None = None,
    session_id: str | None = None,
    occurred_at: datetime | None = None,
    is_offline: bool = False,
) -> PerkInteraction:
    """Insert a single interaction row."""

    resolved_at = occurred_at or datetime.now(timezone.utc)
    if resolved_at.tzinfo is None:
        resolved_at = resolved_at.replace(tzinfo=timezone.utc)

    row = PerkInteraction(
        employee_id=employee_id,
        perk_id=perk_id,
        interaction_type=interaction_type,
        recommendation_rank=recommendation_rank,
        page_context=page_context,
        session_id=session_id,
        is_offline=is_offline,
        occurred_at=resolved_at,
    )
    db.add(row)
    await db.flush()
    return row


async def create_interactions_batch(
    db: AsyncSession,
    rows: list[PerkInteraction],
) -> None:
    """Bulk-insert interaction rows."""

    db.add_all(rows)
    await db.flush()
