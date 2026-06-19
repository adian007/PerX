"""Perk routes with role-aware serialization and catalog browse."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.recommendations import ApiEnvelope
from app.services.perks import browse_catalog, get_perk_for_user
from app.utils.envelope import envelope

router = APIRouter(prefix="/perks", tags=["perks"])


@router.get("", response_model=ApiEnvelope)
async def list_perks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
    category: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Browse active perks from approved providers (employee-safe fields)."""

    if current_user.role != UserRole.employee:
        return envelope({"perks": [], "total": 0, "message": "Use /provider/perks for provider catalog"})

    perks = await browse_catalog(db, category=category, limit=limit)
    payload = [perk.model_dump(mode="json") for perk in perks]
    return envelope({"perks": payload, "total": len(payload)})


@router.get("/featured", response_model=ApiEnvelope)
async def featured_perks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """Return featured perks for the employee home screen."""

    perks = await browse_catalog(db, limit=limit)
    featured = [p for p in perks if p.is_featured][:limit]
    if len(featured) < limit:
        featured = perks[:limit]
    payload = [perk.model_dump(mode="json") for perk in featured]
    return envelope({"perks": payload, "total": len(payload)})


@router.get("/{perk_id}", response_model=ApiEnvelope)
async def get_perk(
    perk_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Return a perk with fields appropriate to the caller's role."""

    data = await get_perk_for_user(db, current_user, perk_id)
    return envelope(data)
