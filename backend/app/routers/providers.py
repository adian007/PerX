"""Provider routes — scoped to own provider_id."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.provider_analytics import ProviderAnalyticsData
from app.schemas.providers import ProviderPerkListData, ProviderProfileData
from app.schemas.recommendations import ApiEnvelope
from app.services.provider_analytics import get_provider_analytics
from app.services.providers import get_provider_profile, list_owned_perks
from app.utils.envelope import envelope

router = APIRouter(prefix="/provider", tags=["providers"])


@router.get("/analytics", response_model=ApiEnvelope)
async def provider_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.provider))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Redemptions, ratings, and demand stats for the authenticated provider."""

    data = await get_provider_analytics(db, current_user)
    return envelope(ProviderAnalyticsData.model_validate(data.model_dump()).model_dump())


@router.get("/profile", response_model=ApiEnvelope)
async def provider_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.provider))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Get the authenticated provider's profile."""

    data = await get_provider_profile(db, current_user)
    return envelope(ProviderProfileData.model_validate(data.model_dump()).model_dump())


@router.get("/perks", response_model=ApiEnvelope)
async def provider_perks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.provider))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """List perks owned by the authenticated provider."""

    data = await list_owned_perks(db, current_user)
    return envelope(ProviderPerkListData.model_validate(data.model_dump()).model_dump())
