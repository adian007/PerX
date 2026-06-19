"""Employer analytics dashboard schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TopPerkStat(BaseModel):
    """Perk popularity within an employer org."""

    model_config = ConfigDict(strict=True)

    perk_id: str
    perk_name: str
    category: str
    selection_count: int
    revenue_cents: int


class CategoryDistribution(BaseModel):
    """Category spend distribution."""

    model_config = ConfigDict(strict=True)

    category: str
    selection_count: int
    spend_cents: int
    pct: float


class EmployerAnalyticsData(BaseModel):
    """GET /employer/analytics response data."""

    model_config = ConfigDict(strict=True)

    period: str
    currency_code: str
    total_payments_cents: int
    completed_payments_count: int
    total_selections: int
    approved_selections: int
    pending_selections: int
    rejected_selections: int
    active_employees: int
    top_perks: list[TopPerkStat]
    category_distribution: list[CategoryDistribution]
