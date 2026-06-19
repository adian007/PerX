"""Employer analytics — payments and selections aggregated by org."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus, SelectionStatus
from app.models.payment import Payment
from app.models.perk import Perk
from app.models.selection import PerkSelection
from app.models.user import User
from app.repositories.budget import current_period
from app.schemas.employer_analytics import (
    CategoryDistribution,
    EmployerAnalyticsData,
    TopPerkStat,
)
from app.services.access_control import require_employer_org


async def get_employer_analytics(
    db: AsyncSession,
    user: User,
    *,
    period: str | None = None,
) -> EmployerAnalyticsData:
    """Return org-scoped analytics from payments and perk selections."""

    org = await require_employer_org(db, user)
    year, month = current_period()
    if period:
        try:
            year_str, month_str = period.split("-", 1)
            year, month = int(year_str), int(month_str)
        except ValueError:
            year, month = current_period()

    period_label = f"{year}-{month:02d}"
    currency_code = org.default_currency_code

    payment_totals = await db.execute(
        select(
            func.coalesce(func.sum(Payment.amount_cents), 0),
            func.count(Payment.id),
        ).where(
            Payment.employer_id == org.id,
            Payment.status == PaymentStatus.completed,
            func.extract("year", Payment.created_at) == year,
            func.extract("month", Payment.created_at) == month,
        )
    )
    total_payments_cents, completed_payments_count = payment_totals.one()
    total_payments_cents = int(total_payments_cents or 0)
    completed_payments_count = int(completed_payments_count or 0)

    selection_counts = await db.execute(
        select(PerkSelection.status, func.count(PerkSelection.id))
        .where(
            PerkSelection.employer_id == org.id,
            func.extract("year", PerkSelection.selected_at) == year,
            func.extract("month", PerkSelection.selected_at) == month,
        )
        .group_by(PerkSelection.status)
    )
    counts_by_status = {row[0]: int(row[1]) for row in selection_counts.all()}
    approved = counts_by_status.get(SelectionStatus.approved, 0)
    pending = counts_by_status.get(SelectionStatus.pending_approval, 0)
    rejected = counts_by_status.get(SelectionStatus.rejected, 0)
    total_selections = sum(counts_by_status.values())

    active_employees = await db.scalar(
        select(func.count(func.distinct(PerkSelection.employee_id))).where(
            PerkSelection.employer_id == org.id,
            func.extract("year", PerkSelection.selected_at) == year,
            func.extract("month", PerkSelection.selected_at) == month,
        )
    )
    active_employees = int(active_employees or 0)

    top_perk_rows = await db.execute(
        select(
            Perk.id,
            Perk.name,
            Perk.category,
            func.count(PerkSelection.id),
            func.coalesce(func.sum(Payment.amount_cents), 0),
        )
        .join(Perk, PerkSelection.perk_id == Perk.id)
        .outerjoin(Payment, Payment.perk_selection_id == PerkSelection.id)
        .where(
            PerkSelection.employer_id == org.id,
            PerkSelection.status == SelectionStatus.approved,
            func.extract("year", PerkSelection.selected_at) == year,
            func.extract("month", PerkSelection.selected_at) == month,
        )
        .group_by(Perk.id, Perk.name, Perk.category)
        .order_by(func.count(PerkSelection.id).desc())
        .limit(5)
    )
    top_perks: list[TopPerkStat] = []
    for perk_id, name, category, count, revenue in top_perk_rows.all():
        cat_value = category.value if hasattr(category, "value") else str(category)
        top_perks.append(
            TopPerkStat(
                perk_id=str(perk_id),
                perk_name=name,
                category=cat_value,
                selection_count=int(count),
                revenue_cents=int(revenue or 0),
            )
        )

    category_rows = await db.execute(
        select(
            Perk.category,
            func.count(PerkSelection.id),
            func.coalesce(func.sum(PerkSelection.price_cents_snapshot), 0),
        )
        .join(Perk, PerkSelection.perk_id == Perk.id)
        .where(
            PerkSelection.employer_id == org.id,
            PerkSelection.status.in_(
                [SelectionStatus.approved, SelectionStatus.pending_approval]
            ),
            func.extract("year", PerkSelection.selected_at) == year,
            func.extract("month", PerkSelection.selected_at) == month,
        )
        .group_by(Perk.category)
        .order_by(func.sum(PerkSelection.price_cents_snapshot).desc())
    )
    category_distribution: list[CategoryDistribution] = []
    total_category_spend = 0
    raw_categories: list[tuple[str, int, int]] = []
    for category, count, spend in category_rows.all():
        cat_value = category.value if hasattr(category, "value") else str(category)
        spend_int = int(spend or 0)
        total_category_spend += spend_int
        raw_categories.append((cat_value, int(count), spend_int))

    for cat_value, count, spend_int in raw_categories:
        pct = round(spend_int / total_category_spend * 100, 1) if total_category_spend else 0.0
        category_distribution.append(
            CategoryDistribution(
                category=cat_value,
                selection_count=count,
                spend_cents=spend_int,
                pct=pct,
            )
        )

    return EmployerAnalyticsData(
        period=period_label,
        currency_code=currency_code,
        total_payments_cents=total_payments_cents,
        completed_payments_count=completed_payments_count,
        total_selections=total_selections,
        approved_selections=approved,
        pending_selections=pending,
        rejected_selections=rejected,
        active_employees=active_employees,
        top_perks=top_perks,
        category_distribution=category_distribution,
    )
