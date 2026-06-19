"""Provider-facing business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.perk import list_provider_perks
from app.schemas.providers import ProviderPerkListData, ProviderProfileData
from app.services.access_control import require_provider_profile
from app.services.perks import perk_for_provider


async def get_provider_profile(db: AsyncSession, user: User) -> ProviderProfileData:
    """Return the authenticated provider's profile."""

    provider = await require_provider_profile(db, user)
    return ProviderProfileData(
        id=str(provider.id),
        company_name=provider.company_name,
        description=provider.description,
        logo_url=provider.logo_url,
        website_url=provider.website_url,
        status=provider.status.value,
        avg_rating=float(provider.avg_rating or 0.0),
        total_perks=provider.total_perks,
    )


async def list_owned_perks(db: AsyncSession, user: User) -> ProviderPerkListData:
    """List perks owned by the authenticated provider."""

    provider = await require_provider_profile(db, user)
    perks = await list_provider_perks(db, provider.id)
    return ProviderPerkListData(
        perks=[perk_for_provider(perk, user).model_dump(mode="json") for perk in perks],
        total=len(perks),
    )
