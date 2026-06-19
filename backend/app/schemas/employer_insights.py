"""Employer analytics / insights API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CategoryInsight(BaseModel):
    """Per-category selection summary for employer dashboard."""

    model_config = ConfigDict(strict=True)

    category: str
    selection_count: int
    spent_cents: int


class EmployerInsightsData(BaseModel):
    """GET /employer/insights response data."""

    model_config = ConfigDict(strict=True)

    period: str
    currency_code: str
    employee_count: int
    total_allocated_cents: int
    total_spent_cents: int
    total_pending_cents: int
    total_remaining_cents: int
    unused_budget_cents: int
    utilization_pct: float
    pending_approval_count: int
    top_categories: list[CategoryInsight]
    allocated_formatted: str
    spent_formatted: str
    pending_formatted: str
    remaining_formatted: str
    insight_summary: str
