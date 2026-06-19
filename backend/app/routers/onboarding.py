"""Onboarding routes — JWT employee path + optional demo mode."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_optional_current_user
from app.config import get_settings
from app.database import get_db
from app.middleware.rate_limit import enforce_optional_rate_limit
from app.models.enums import UserRole
from app.models.recommendation import EmployeeProfile as DemoEmployeeProfile
from app.models.user import User
from app.schemas.onboarding import (
    OnboardingExplanationData,
    OnboardingRequest,
    OnboardingResponseData,
)
from app.schemas.recommendations import ApiEnvelope
from app.services.access_control import assert_role, require_employee_profile
from app.services.onboarding_service import get_onboarding_explanation, persist_onboarding
from app.services.recommendation.demo_store import (
    DEMO_NEW_EMPLOYEE,
    get_current_demo_employee_id,
    save_onboarded_profile,
    set_current_demo_employee_id,
)
from app.services.recommendation.onboarding import complete_onboarding
from app.utils.envelope import envelope
from app.utils.ollama import EXPLANATION_STORE, generate_and_store_explanation

router = APIRouter(tags=["onboarding"])


async def _complete_demo_onboarding(
    body: OnboardingRequest,
    background_tasks: BackgroundTasks,
) -> OnboardingResponseData:
    """Legacy demo path when ALLOW_DEMO_MODE is enabled and no JWT is sent."""

    result = complete_onboarding(
        lifestyle_tags=body.lifestyle_tags,
        preferred_categories=body.preferred_categories,
        budget_sensitivity=body.budget_sensitivity,
        wellness_priority=body.wellness_priority,
        family_situation=body.family_situation,
    )

    profile = DemoEmployeeProfile(
        id=DEMO_NEW_EMPLOYEE.id,
        first_name=DEMO_NEW_EMPLOYEE.first_name,
        interaction_count=0,
        recommender_mode="cold_start",
        lifestyle_tags=body.lifestyle_tags,
        preferred_categories=body.preferred_categories,
        budget_sensitivity=body.budget_sensitivity,
        wellness_priority=body.wellness_priority,
        family_situation=body.family_situation,
        affinity_vector=result.affinity_vector,
    )
    save_onboarded_profile(profile)
    set_current_demo_employee_id(profile.id)

    from app.config import get_settings

    settings = get_settings()
    background_tasks.add_task(
        generate_and_store_explanation,
        profile.id,
        result.affinity_vector,
        result.top_categories,
        profile.first_name,
        settings,
    )

    return OnboardingResponseData(
        onboarding_completed=result.onboarding_completed,
        affinity_vector=result.affinity_vector,
        explanation_pending=True,
        explanation=None,
    )


@router.post("/me/onboarding", response_model=ApiEnvelope)
async def complete_onboarding_route(
    body: OnboardingRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    _: Annotated[None, Depends(enforce_optional_rate_limit)],
) -> dict:
    """Complete the 5-question onboarding form and trigger async LLM explanation."""

    if current_user is not None:
        assert_role(current_user, {UserRole.employee})
        persisted = await persist_onboarding(db, current_user, body)
        profile = await require_employee_profile(db, current_user)
        settings = get_settings()
        background_tasks.add_task(
            generate_and_store_explanation,
            str(profile.id),
            persisted.response.affinity_vector,
            persisted.top_categories,
            persisted.employee_name,
            settings,
        )
        data = persisted.response
    else:
        if not get_settings().allow_demo_mode:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required",
                    "details": {},
                },
            )
        data = await _complete_demo_onboarding(body, background_tasks)

    return envelope(data.model_dump())


@router.get("/me/onboarding/explanation", response_model=ApiEnvelope)
async def get_onboarding_explanation_route(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    _: Annotated[None, Depends(enforce_optional_rate_limit)],
) -> dict:
    """Poll for the async LLM explanation after onboarding."""

    if current_user is not None:
        assert_role(current_user, {UserRole.employee})
        profile = await require_employee_profile(db, current_user)
        explanation = profile.welcome_explanation or EXPLANATION_STORE.get(str(profile.id))
        data = OnboardingExplanationData(
            ready=explanation is not None,
            explanation=explanation,
        )
    else:
        if not get_settings().allow_demo_mode:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required",
                    "details": {},
                },
            )
        employee_id = get_current_demo_employee_id()
        explanation = EXPLANATION_STORE.get(employee_id)
        data = OnboardingExplanationData(
            ready=explanation is not None,
            explanation=explanation,
        )

    return envelope(data.model_dump())
