"""Onboarding business logic for the recommendation engine."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.recommendation.cold_start import (
    compute_affinity_vector,
    top_affinity_categories,
)


@dataclass(frozen=True)
class OnboardingResult:
    """Result of completing the 5-question onboarding form."""

    affinity_vector: dict[str, float]
    top_categories: list[str]
    onboarding_completed: bool = True


def complete_onboarding(
    lifestyle_tags: list[str],
    preferred_categories: list[str],
    budget_sensitivity: str,
    wellness_priority: int,
    family_situation: str,
) -> OnboardingResult:
    """Compute affinity from onboarding answers.

    Pure deterministic function — persistence is handled by the router layer.
    """

    affinity_vector = compute_affinity_vector(
        lifestyle_tags=lifestyle_tags,
        preferred_categories=preferred_categories,
        budget_sensitivity=budget_sensitivity,
        wellness_priority=wellness_priority,
        family_situation=family_situation,
    )
    return OnboardingResult(
        affinity_vector=affinity_vector,
        top_categories=top_affinity_categories(affinity_vector),
    )
