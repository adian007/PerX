"""Employee-facing business logic."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import EmployeeProfile
from app.models.user import User
from app.repositories.budget import get_current_allocation
from app.schemas.employees import BudgetSummaryData, EmployeeMeData, EmployerSummary
from app.services.access_control import require_employee_profile
from app.services.recommendation.mode import determine_recommender_mode
from app.utils.formatting import format_money


async def get_employee_me(db: AsyncSession, user: User) -> EmployeeMeData:
    """Build the GET /me response for the authenticated employee."""

    profile = await require_employee_profile(db, user)
    employer = profile.employer
    mode = determine_recommender_mode(
        profile.interaction_count,
        profile.recommender_mode,  # type: ignore[arg-type]
    )

    return EmployeeMeData(
        id=str(profile.id),
        email=user.email,
        first_name=profile.first_name,
        last_name=profile.last_name,
        avatar_url=profile.avatar_url,
        department=profile.department,
        job_title=profile.job_title,
        onboarding_completed=profile.onboarding_completed,
        recommender_mode=mode,
        interaction_count=profile.interaction_count,
        locale=user.locale,
        currency_code=employer.default_currency_code,
        employer=EmployerSummary(
            id=str(employer.id),
            organization_name=employer.organization_name,
            logo_url=employer.logo_url,
        ),
    )


async def get_employee_budget(db: AsyncSession, user: User) -> BudgetSummaryData:
    """Return current-month budget state for the authenticated employee."""

    profile = await require_employee_profile(db, user)
    allocation = await get_current_allocation(db, profile.id)
    now = datetime.now(timezone.utc)
    period = f"{now.year}-{now.month:02d}"

    currency_code = profile.employer.default_currency_code
    locale = user.locale

    if allocation is None:
        return BudgetSummaryData(
            period=period,
            allocated_cents=0,
            spent_cents=0,
            pending_cents=0,
            remaining_cents=0,
            currency_code=currency_code,
            allocated_formatted=format_money(0, currency_code=currency_code, locale=locale),
            spent_formatted=format_money(0, currency_code=currency_code, locale=locale),
            pending_formatted=format_money(0, currency_code=currency_code, locale=locale),
            remaining_formatted=format_money(0, currency_code=currency_code, locale=locale),
        )

    utilization = 0.0
    if allocation.allocated_cents > 0:
        utilization = round(
            (allocation.spent_cents + allocation.pending_cents) / allocation.allocated_cents * 100,
            1,
        )

    currency_code = allocation.currency_code
    locale = user.locale

    return BudgetSummaryData(
        period=period,
        allocated_cents=allocation.allocated_cents,
        spent_cents=allocation.spent_cents,
        pending_cents=allocation.pending_cents,
        remaining_cents=allocation.remaining_cents,
        currency_code=currency_code,
        utilization_pct=utilization,
        allocated_formatted=format_money(
            allocation.allocated_cents, currency_code=currency_code, locale=locale
        ),
        spent_formatted=format_money(
            allocation.spent_cents, currency_code=currency_code, locale=locale
        ),
        pending_formatted=format_money(
            allocation.pending_cents, currency_code=currency_code, locale=locale
        ),
        remaining_formatted=format_money(
            allocation.remaining_cents, currency_code=currency_code, locale=locale
        ),
    )
