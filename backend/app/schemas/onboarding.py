"""Pydantic schemas for onboarding endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    """Body for POST /me/onboarding per api-contract."""

    lifestyle_tags: list[str]
    preferred_categories: list[str]
    budget_sensitivity: str = "medium"
    wellness_priority: int = Field(default=5, ge=1, le=10)
    family_situation: str = "single"


class OnboardingResponseData(BaseModel):
    """Onboarding completion response data."""

    onboarding_completed: bool
    affinity_vector: dict[str, float]
    explanation_pending: bool
    explanation: str | None


class OnboardingExplanationData(BaseModel):
    """Poll response for async LLM explanation."""

    ready: bool
    explanation: str | None
