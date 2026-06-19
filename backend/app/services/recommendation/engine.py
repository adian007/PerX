"""Recommendation orchestration service."""

from __future__ import annotations

import time
from typing import Any

from fastapi import BackgroundTasks

from app.config import Settings, get_settings
from app.models.recommendation import EmployeeProfile, Perk
from app.services.recommendation.cache import (
    RECOMMENDATION_CACHE_TTL_SECONDS,
    RecommendationCache,
    recommendation_cache,
)
from app.services.recommendation.cold_start import (
    compute_affinity_vector,
    score_cold_start_recommendations,
    top_affinity_categories,
)
from app.services.recommendation.hybrid import compute_warm_recommendations
from app.services.recommendation.mode import mode_for_employee
from app.utils.ollama import generate_and_store_explanation, get_fallback_explanation


def affinity_for_employee(employee: EmployeeProfile) -> dict[str, float]:
    """Return stored affinity or compute it from onboarding fields."""

    if employee.affinity_vector:
        return employee.affinity_vector
    return compute_affinity_vector(
        lifestyle_tags=employee.lifestyle_tags,
        preferred_categories=employee.preferred_categories,
        budget_sensitivity=employee.budget_sensitivity,
        wellness_priority=employee.wellness_priority,
        family_situation=employee.family_situation,
    )


def _compute_recommendation_payload(
    employee: EmployeeProfile,
    available_perks: list[Perk],
    budget_remaining_cents: int,
    ucb_counts: dict[str, int] | None,
    cf_scores: dict[str, float] | None,
    limit: int,
    category: str | None,
    include_score_breakdown: bool,
    settings: Settings,
) -> dict[str, Any]:
    """Compute recommendations without cache or background tasks."""

    mode = mode_for_employee(
        employee,
        warm_threshold=settings.recommender_warm_threshold,
    )
    affinity_vector = affinity_for_employee(employee)
    top_categories = top_affinity_categories(affinity_vector)

    if mode == "warm":
        recommendations = compute_warm_recommendations(
            affinity_vector=affinity_vector,
            available_perks=available_perks,
            budget_remaining_cents=budget_remaining_cents,
            ucb_counts=ucb_counts or {},
            cf_scores=cf_scores,
            limit=limit,
            category=category,
        )
    else:
        recommendations = score_cold_start_recommendations(
            affinity_vector=affinity_vector,
            available_perks=available_perks,
            budget_remaining_cents=budget_remaining_cents,
            limit=limit,
            category=category,
        )

    return {
        "mode": mode,
        "perks": [
            recommendation.to_api_dict(
                include_score_breakdown=include_score_breakdown
            )
            for recommendation in recommendations
        ],
        "total": len(recommendations),
        "explanation_pending": True,
        "explanation": get_fallback_explanation(top_categories[0], employee.first_name),
        "_affinity_vector": affinity_vector,
        "_top_categories": top_categories,
    }


async def build_recommendation_payload(
    employee: EmployeeProfile,
    available_perks: list[Perk],
    background_tasks: BackgroundTasks,
    budget_remaining_cents: int,
    ucb_counts: dict[str, int] | None = None,
    cf_scores: dict[str, float] | None = None,
    limit: int = 20,
    category: str | None = None,
    refresh: bool = False,
    include_score_breakdown: bool = False,
    settings: Settings | None = None,
    cache: RecommendationCache | None = None,
) -> dict[str, Any]:
    """Build a complete recommendation response without waiting on the LLM."""

    active_settings = settings or get_settings()
    active_cache = cache if cache is not None else recommendation_cache
    cache_key = _cache_key(employee.id, limit, category, include_score_breakdown)

    if not refresh:
        cached = await active_cache.get(cache_key)
        if cached is not None:
            payload = dict(cached.payload)
            payload["cached"] = True
            payload["cache_age_seconds"] = max(
                0, int(time.monotonic() - cached.cached_at)
            )
            return payload

    computed = _compute_recommendation_payload(
        employee=employee,
        available_perks=available_perks,
        budget_remaining_cents=budget_remaining_cents,
        ucb_counts=ucb_counts,
        cf_scores=cf_scores,
        limit=limit,
        category=category,
        include_score_breakdown=include_score_breakdown,
        settings=active_settings,
    )

    background_tasks.add_task(
        generate_and_store_explanation,
        employee.id,
        computed["_affinity_vector"],
        computed["_top_categories"],
        employee.first_name,
        active_settings,
    )

    storable = {
        key: value
        for key, value in computed.items()
        if not key.startswith("_")
    }
    storable["cached"] = False
    storable["cache_age_seconds"] = 0

    await active_cache.set(
        cache_key,
        storable,
        ttl_seconds=RECOMMENDATION_CACHE_TTL_SECONDS,
    )

    return storable


def _cache_key(
    employee_id: str,
    limit: int,
    category: str | None,
    include_score_breakdown: bool,
) -> str:
    """Build a cache key that includes query parameters."""

    category_part = category or "*"
    breakdown_part = "1" if include_score_breakdown else "0"
    return f"{employee_id}:{limit}:{category_part}:{breakdown_part}"
