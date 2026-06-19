"""Database-backed onboarding service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import EmployeeProfile
from app.models.user import User
from app.schemas.onboarding import OnboardingExplanationData, OnboardingRequest, OnboardingResponseData
from app.services.access_control import require_employee_profile
from app.services.recommendation.onboarding import complete_onboarding


@dataclass(frozen=True)
class OnboardingPersistResult:
    """Result of persisting onboarding including LLM task metadata."""

    response: OnboardingResponseData
    top_categories: list[str]
    employee_name: str


async def persist_onboarding(
    db: AsyncSession,
    user: User,
    body: OnboardingRequest,
) -> OnboardingPersistResult:
    """Complete onboarding for an authenticated employee and persist affinity."""

    profile = await require_employee_profile(db, user)
    result = complete_onboarding(
        lifestyle_tags=body.lifestyle_tags,
        preferred_categories=body.preferred_categories,
        budget_sensitivity=body.budget_sensitivity,
        wellness_priority=body.wellness_priority,
        family_situation=body.family_situation,
    )

    profile.lifestyle_tags = body.lifestyle_tags
    profile.preferred_categories = body.preferred_categories
    profile.budget_sensitivity = body.budget_sensitivity
    profile.wellness_priority = body.wellness_priority
    profile.family_situation = body.family_situation
    profile.affinity_vector = result.affinity_vector
    profile.affinity_updated_at = datetime.now(timezone.utc)
    profile.onboarding_completed = True
    profile.welcome_explanation = None
    await db.flush()

    return OnboardingPersistResult(
        response=OnboardingResponseData(
            onboarding_completed=True,
            affinity_vector=result.affinity_vector,
            explanation_pending=True,
            explanation=None,
        ),
        top_categories=result.top_categories,
        employee_name=profile.first_name,
    )


def get_onboarding_explanation(profile: EmployeeProfile) -> OnboardingExplanationData:
    """Poll stored welcome explanation for an employee profile."""

    explanation = profile.welcome_explanation
    return OnboardingExplanationData(
        ready=explanation is not None,
        explanation=explanation,
    )
