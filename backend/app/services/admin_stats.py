"""Platform admin statistics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.models.enums import ProviderStatus, UserRole
from app.models.provider import ProviderProfile
from app.models.user import User


class PendingProviderItem(BaseModel):
    """Provider awaiting platform review."""

    model_config = ConfigDict(strict=True)

    id: str
    company_name: str
    user_email: str


class AdminStatsData(BaseModel):
    """GET /admin/stats response data."""

    model_config = ConfigDict(strict=True)

    users_total: int
    employees_total: int
    employers_total: int
    providers_total: int
    providers_pending_review: int
    pending_providers: list[PendingProviderItem]


async def get_admin_stats(db: AsyncSession) -> AdminStatsData:
    """Return platform-wide counts and pending provider review queue."""

    role_counts = await db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    by_role = {row[0]: int(row[1]) for row in role_counts.all()}

    pending_rows = (
        await db.scalars(
            select(ProviderProfile)
            .options(selectinload(ProviderProfile.user))
            .where(ProviderProfile.status == ProviderStatus.pending_review)
            .order_by(ProviderProfile.created_at.desc())
            .limit(20)
        )
    ).all()

    pending_providers: list[PendingProviderItem] = []
    for provider in pending_rows:
        pending_providers.append(
            PendingProviderItem(
                id=str(provider.id),
                company_name=provider.company_name,
                user_email=provider.user.email if provider.user else "",
            )
        )

    providers_pending = await db.scalar(
        select(func.count(ProviderProfile.id)).where(
            ProviderProfile.status == ProviderStatus.pending_review
        )
    )

    users_total = sum(by_role.values())
    return AdminStatsData(
        users_total=users_total,
        employees_total=by_role.get(UserRole.employee, 0),
        employers_total=by_role.get(UserRole.employer, 0),
        providers_total=by_role.get(UserRole.provider, 0),
        providers_pending_review=int(providers_pending or 0),
        pending_providers=pending_providers,
    )
