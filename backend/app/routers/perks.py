"""Perk routes with role-aware serialization."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.perk import Perk
from app.models.user import User
from app.schemas.recommendations import ApiEnvelope
from app.services.perks import perk_for_employee, perk_for_provider
from app.utils.envelope import envelope

router = APIRouter(prefix="/perks", tags=["perks"])


@router.get("/{perk_id}", response_model=ApiEnvelope)
async def get_perk(
    perk_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Return a perk with fields appropriate to the caller's role."""

    perk = await db.scalar(select(Perk).where(Perk.id == perk_id))
    if perk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERK_NOT_FOUND",
                "message": "Perk not found",
                "details": {},
            },
        )

    if current_user.role == UserRole.employee:
        data = perk_for_employee(perk).model_dump(mode="json")
    else:
        data = perk_for_provider(perk, current_user).model_dump(mode="json")

    return envelope(data)
