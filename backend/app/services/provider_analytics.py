"""Provider-side analytics stub — own perk and payment stats."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus, SelectionStatus
from app.models.payment import Payment
from app.models.perk import Perk
from app.models.selection import PerkSelection
from app.models.user import User
from app.schemas.provider_analytics import (
    ProviderAnalyticsData,
    ProviderCategoryDemand,
    ProviderPerkStat,
)
from app.services.access_control import require_provider_profile


async def get_provider_analytics(db: AsyncSession, user: User) -> ProviderAnalyticsData:
    """Aggregate redemption and revenue stats for the authenticated provider."""

    provider = await require_provider_profile(db, user)

    payment_totals = await db.execute(
        select(
            func.coalesce(func.sum(Payment.amount_cents), 0),
            func.count(Payment.id),
        ).where(
            Payment.provider_id == provider.id,
            Payment.status == PaymentStatus.completed,
        )
    )
    total_revenue_cents, completed_payments_count = payment_totals.one()

    perk_rows = await db.execute(
        select(
            Perk.id,
            Perk.name,
            Perk.category,
            func.count(PerkSelection.id),
            func.coalesce(func.sum(Payment.amount_cents), 0),
        )
        .outerjoin(PerkSelection, PerkSelection.perk_id == Perk.id)
        .outerjoin(
            Payment,
            (Payment.perk_selection_id == PerkSelection.id)
            & (Payment.status == PaymentStatus.completed),
        )
        .where(Perk.provider_id == provider.id, Perk.is_active.is_(True))
        .group_by(Perk.id, Perk.name, Perk.category)
        .order_by(func.count(PerkSelection.id).desc())
    )

    perk_stats: list[ProviderPerkStat] = []
    category_counts: dict[str, int] = {}
    for perk_id, name, category, count, revenue in perk_rows.all():
        cat_value = category.value if hasattr(category, "value") else str(category)
        selection_count = int(count or 0)
        perk_stats.append(
            ProviderPerkStat(
                perk_id=str(perk_id),
                perk_name=name,
                category=cat_value,
                selection_count=selection_count,
                revenue_cents=int(revenue or 0),
            )
        )
        category_counts[cat_value] = category_counts.get(cat_value, 0) + selection_count

    demand_by_category = [
        ProviderCategoryDemand(category=cat, selection_count=count)
        for cat, count in sorted(category_counts.items(), key=lambda item: item[1], reverse=True)
    ]

    return ProviderAnalyticsData(
        total_perks=provider.total_perks,
        total_redemptions=provider.total_redemptions,
        avg_rating=float(provider.avg_rating or 0.0),
        total_revenue_cents=int(total_revenue_cents or 0),
        completed_payments_count=int(completed_payments_count or 0),
        perk_stats=perk_stats,
        demand_by_category=demand_by_category,
    )
