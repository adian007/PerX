"""Recommendation routes — JWT employee path + optional demo mode."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_optional_current_user
from app.config import get_settings
from app.database import get_db
from app.middleware.rate_limit import enforce_optional_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.recommendations import (
    ApiEnvelope,
    RecommendationCategoriesData,
    RecommendationExplanationData,
    RecommendationResponseData,
)
from app.services.access_control import assert_role, require_employee_profile
from app.services.recommendation.cache import recommendation_cache
from app.services.recommendation.context import load_recommendation_context
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


def _resolve_demo_profile(
    demo: DemoProfile | None,
    warm_demo: bool,
) -> DemoProfile:
    if demo is not None:
        return demo
    return "warm" if warm_demo else "cold"


async def _employee_context_or_demo(
    db: AsyncSession,
    current_user: User | None,
    demo: DemoProfile | None,
    warm_demo: bool,
):
    """Use DB-backed context when authenticated; demo store when demo mode allows."""

    if current_user is not None:
        assert_role(current_user, {UserRole.employee})
        return await load_recommendation_context(db, current_user)

    settings = get_settings()
    if not settings.allow_demo_mode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Authentication required",
                "details": {},
            },
        )

    profile_key = resolve_demo_profile(demo=_resolve_demo_profile(demo, warm_demo), warm_demo=warm_demo)
    employee = get_demo_employee(demo=profile_key)
    return employee, get_demo_perks(), 5000, DEMO_UCB_COUNTS


@router.get("/recommendations", response_model=ApiEnvelope)
async def get_recommendations(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    _: Annotated[None, Depends(enforce_optional_rate_limit)],
    limit: int = Query(20, ge=1, le=50),
    category: str | None = None,
    refresh: bool = False,
    include_score_breakdown: bool = False,
    demo: DemoProfile | None = Query(default=None),
    warm_demo: bool = False,
) -> dict:
    """Get personalized recommendations for the current employee."""

    employee, available_perks, budget_remaining, ucb_counts = await _employee_context_or_demo(
        db, current_user, demo, warm_demo
    )

    data = await build_recommendation_payload(
        employee=employee,
        available_perks=available_perks,
        background_tasks=background_tasks,
        budget_remaining_cents=budget_remaining,
        ucb_counts=ucb_counts,
        limit=limit,
        category=category,
        refresh=refresh,
        include_score_breakdown=include_score_breakdown,
        cache=recommendation_cache,
    )
    return envelope(RecommendationResponseData.model_validate(data).model_dump())


@router.get("/recommendations/categories", response_model=ApiEnvelope)
async def get_recommendation_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    _: Annotated[None, Depends(enforce_optional_rate_limit)],
    demo: DemoProfile | None = Query(default=None),
    warm_demo: bool = False,
) -> dict:
    """Get category-level affinity breakdown for the current employee."""

    employee, catalog, _, _ = await _employee_context_or_demo(db, current_user, demo, warm_demo)
    affinity_vector = affinity_for_employee(employee)
    data = RecommendationCategoriesData(
        categories=[
            {
                "category": cat,
                "score": score,
                "perk_count": sum(1 for perk in catalog if perk.category == cat),
                "color": CATEGORY_COLORS.get(cat, "#A0AEC0"),
            }
            for cat, score in affinity_vector.items()
        ]
    )
    return envelope(data.model_dump())


@router.get("/recommendations/explanation", response_model=ApiEnvelope)
async def get_recommendation_explanation(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    _: Annotated[None, Depends(enforce_optional_rate_limit)],
    demo: DemoProfile | None = Query(default=None),
    warm_demo: bool = False,
) -> dict:
    """Poll for the async recommendation explanation."""

    if current_user is not None:
        assert_role(current_user, {UserRole.employee})
        profile = await require_employee_profile(db, current_user)
        explanation = profile.welcome_explanation or EXPLANATION_STORE.get(str(profile.id))
    else:
        settings = get_settings()
        if not settings.allow_demo_mode:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required",
                    "details": {},
                },
            )
        profile_key = resolve_demo_profile(
            demo=_resolve_demo_profile(demo, warm_demo),
            warm_demo=warm_demo,
        )
        employee = get_demo_employee(demo=profile_key)
        explanation = EXPLANATION_STORE.get(employee.id)
        if explanation is None and profile_key == "cold":
            explanation = EXPLANATION_STORE.get(get_current_demo_employee_id())

    data = RecommendationExplanationData(
        ready=explanation is not None,
        explanation=explanation,
    )
    return envelope(data.model_dump())
