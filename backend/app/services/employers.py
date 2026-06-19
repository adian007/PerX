"""Employer-facing business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.employers import EmployerOrganizationData
from app.services.access_control import require_employer_org


async def get_employer_organization(db: AsyncSession, user: User) -> EmployerOrganizationData:
    """Return the authenticated employer's organization profile."""

    org = await require_employer_org(db, user)
    return EmployerOrganizationData(
        id=str(org.id),
        organization_name=org.organization_name,
        logo_url=org.logo_url,
        contact_name=org.contact_name,
        default_monthly_budget_cents=org.default_monthly_budget_cents,
        default_currency_code=org.default_currency_code,
        require_approval=org.require_approval,
        invite_code=org.invite_code,
    )
