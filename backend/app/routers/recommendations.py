"""Recommendation routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query

from app.schemas.recommendations import (
    ApiEnvelope,
    RecommendationCategoriesData,
    RecommendationExplanationData,
    RecommendationResponseData,
)
from app.services.recommendation.cache import recommendation_cache
from app.services.recommendation.demo_store import (
    DEMO_UCB_COUNTS,
    DemoProfile,
    get_current_demo_employee_id,
    get_demo_employee,
    get_demo_perks,
    resolve_demo_profile,
)
from app.services.recommendation.engine import affinity_for_employee, build_recommendation_payload
from app.utils.envelope import envelope
from app.utils.ollama import EXPLANATION_STORE

router = APIRouter(tags=["recommendations"])

CATEGORY_COLORS = {
    "fitness": "#FF6B35",
    "wellness": "#4ECDC4",
    "food": "#45B7D1",
    "transport": "#96E6A1",
    "education": "#DDA0DD",
    "travel": "#F4A261",
    "entertainment": "#8E7DBE",
    "childcare": "#2A9D8F",
    "other": "#A0AEC0",
}


@router.get("/recommendations", response_model=ApiEnvelope)
async def get_recommendations(
    background_tasks: BackgroundTasks,
    limit: int = Query(20, ge=1, le=50),
    category: str | None = None,
    refresh: bool = False,
    include_score_breakdown: bool = False,
    demo: DemoProfile = "cold",
    warm_demo: bool = False,
) -> dict:
    """Get personalized recommendations for the current employee."""

    profile_key = resolve_demo_profile(demo=demo, warm_demo=warm_demo)
    employee = get_demo_employee(demo=profile_key)
    data = await build_recommendation_payload(
        employee=employee,
        available_perks=get_demo_perks(),
        background_tasks=background_tasks,
        budget_remaining_cents=5000,
        ucb_counts=DEMO_UCB_COUNTS,
        limit=limit,
        category=category,
        refresh=refresh,
        include_score_breakdown=include_score_breakdown,
        cache=recommendation_cache,
    )
    return envelope(RecommendationResponseData.model_validate(data).model_dump())


@router.get("/recommendations/categories", response_model=ApiEnvelope)
async def get_recommendation_categories(
    demo: DemoProfile = "cold",
    warm_demo: bool = False,
) -> dict:
    """Get category-level affinity breakdown for the current employee."""

    profile_key = resolve_demo_profile(demo=demo, warm_demo=warm_demo)
    affinity_vector = affinity_for_employee(get_demo_employee(demo=profile_key))
    data = RecommendationCategoriesData(
        categories=[
            {
                "category": category,
                "score": score,
                "perk_count": sum(
                    1 for perk in get_demo_perks() if perk.category == category
                ),
                "color": CATEGORY_COLORS.get(category, "#A0AEC0"),
            }
            for category, score in affinity_vector.items()
        ]
    )
    return envelope(data.model_dump())


@router.get("/recommendations/explanation", response_model=ApiEnvelope)
async def get_recommendation_explanation(
    demo: DemoProfile = "cold",
    warm_demo: bool = False,
) -> dict:
    """Poll for the async recommendation explanation."""

    profile_key = resolve_demo_profile(demo=demo, warm_demo=warm_demo)
    employee = get_demo_employee(demo=profile_key)
    explanation = EXPLANATION_STORE.get(employee.id)
    if explanation is None and profile_key == "cold":
        explanation = EXPLANATION_STORE.get(get_current_demo_employee_id())

    data = RecommendationExplanationData(
        ready=explanation is not None,
        explanation=explanation,
    )
    return envelope(data.model_dump())
