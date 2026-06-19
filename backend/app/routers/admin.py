"""Admin routes — platform management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.recommendations import ApiEnvelope
from app.services.admin_stats import get_admin_stats
from app.utils.envelope import envelope

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=ApiEnvelope)
async def admin_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Platform-wide stats and pending provider review queue."""

    data = await get_admin_stats(db)
    return envelope(data.model_dump())
