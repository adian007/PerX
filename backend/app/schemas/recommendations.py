"""Pydantic schemas for recommendation endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderResponse(BaseModel):
    """Provider fields exposed on a recommendation."""

    id: str
    company_name: str
    logo_url: str | None
    avg_rating: float


class ScoreBreakdownResponse(BaseModel):
    """Warm-mode score components."""

    model_config = ConfigDict(populate_by_name=True)

    content_score: float
    cf_score: float = Field(alias="cf_score")
    ucb_bonus: float
    final_score: float


class RecommendationPerkResponse(BaseModel):
    """Recommended perk response shape."""

    id: str
    name: str
    category: str
    short_description: str
    image_url: str | None
    employee_price_cents: int
    employee_price_formatted: str
    provider: ProviderResponse
    recommendation_score: float
    reason_code: str
    reason_text: str
    tags: list[str]
    is_affordable: bool
    is_featured: bool
    score_breakdown: ScoreBreakdownResponse | None = None


class RecommendationResponseData(BaseModel):
    """Top-level recommendation response data."""

    mode: str
    perks: list[RecommendationPerkResponse]
    total: int
    cached: bool
    cache_age_seconds: int
    explanation_pending: bool
    explanation: str


class RecommendationExplanationData(BaseModel):
    """Poll response for recommendation explanation."""

    ready: bool
    explanation: str | None


class CategoryBreakdownItem(BaseModel):
    """Category affinity item for globe visualization."""

    category: str
    score: float
    perk_count: int
    color: str


class RecommendationCategoriesData(BaseModel):
    """Category breakdown response data."""

    categories: list[CategoryBreakdownItem]


class ResponseMeta(BaseModel):
    """Standard PerX API response meta."""

    timestamp: str
    request_id: str


class ApiEnvelope(BaseModel):
    """Standard PerX API response envelope."""

    data: Any
    meta: ResponseMeta
