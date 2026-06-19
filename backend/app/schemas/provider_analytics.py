"""Provider analytics schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProviderPerkStat(BaseModel):
    """Per-perk stats for provider dashboard."""

    model_config = ConfigDict(strict=True)

    perk_id: str
    perk_name: str
    category: str
    selection_count: int
    revenue_cents: int


class ProviderCategoryDemand(BaseModel):
    """Demand by category for provider offerings."""

    model_config = ConfigDict(strict=True)

    category: str
    selection_count: int


class ProviderAnalyticsData(BaseModel):
    """GET /provider/analytics response data."""

    model_config = ConfigDict(strict=True)

    total_perks: int
    total_redemptions: int
    avg_rating: float
    total_revenue_cents: int
    completed_payments_count: int
    perk_stats: list[ProviderPerkStat]
    demand_by_category: list[ProviderCategoryDemand]
