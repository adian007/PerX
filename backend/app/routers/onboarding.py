"""Onboarding routes (demo — no auth/DB)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.config import get_settings
from app.models.recommendation import EmployeeProfile
from app.schemas.onboarding import (
    OnboardingExplanationData,
    OnboardingRequest,
    OnboardingResponseData,
)
from app.schemas.recommendations import ApiEnvelope
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


@router.post("/me/onboarding", response_model=ApiEnvelope)
async def complete_onboarding_route(
    body: OnboardingRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """Complete the 5-question onboarding form and trigger async LLM explanation."""

    result = complete_onboarding(
        lifestyle_tags=body.lifestyle_tags,
        preferred_categories=body.preferred_categories,
        budget_sensitivity=body.budget_sensitivity,
        wellness_priority=body.wellness_priority,
        family_situation=body.family_situation,
    )

    profile = EmployeeProfile(
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

    settings = get_settings()
    background_tasks.add_task(
        generate_and_store_explanation,
        profile.id,
        result.affinity_vector,
        result.top_categories,
        profile.first_name,
        settings,
    )

    data = OnboardingResponseData(
        onboarding_completed=result.onboarding_completed,
        affinity_vector=result.affinity_vector,
        explanation_pending=True,
        explanation=None,
    )
    return envelope(data.model_dump())


@router.get("/me/onboarding/explanation", response_model=ApiEnvelope)
async def get_onboarding_explanation() -> dict:
    """Poll for the async LLM explanation after onboarding."""

    employee_id = get_current_demo_employee_id()
    explanation = EXPLANATION_STORE.get(employee_id)
    data = OnboardingExplanationData(
        ready=explanation is not None,
        explanation=explanation,
    )
    return envelope(data.model_dump())
