"""Provider API response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProviderProfileData(BaseModel):
    """GET /provider/profile response data."""

    model_config = ConfigDict(strict=True)

    id: str
    company_name: str
    description: str | None = None
    logo_url: str | None = None
    website_url: str | None = None
    status: str
    avg_rating: float
    total_perks: int


class ProviderPerkListData(BaseModel):
    """GET /provider/perks response data."""

    model_config = ConfigDict(strict=True)

    perks: list[dict]
    total: int
