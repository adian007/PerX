"""Employer-side analytics for budget utilization and category popularity."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.enums import SelectionStatus
from app.models.perk import Perk
from app.models.selection import PerkSelection
from app.models.user import User
from app.repositories.budget import current_period
from app.schemas.employer_insights import CategoryInsight, EmployerInsightsData
from app.services.access_control import require_employer_org
from app.utils.formatting import format_money


async def get_employer_insights(db: AsyncSession, user: User) -> EmployerInsightsData:
    """Aggregate org-wide budget and selection metrics for the current period."""

    org = await require_employer_org(db, user)
    year, month = current_period()
    period = f"{year}-{month:02d}"
    currency_code = org.default_currency_code
    locale = user.locale

    allocations = (
        await db.scalars(
            select(BudgetAllocation).where(
                BudgetAllocation.employer_id == org.id,
                BudgetAllocation.period_year == year,
                BudgetAllocation.period_month == month,
            )
        )
    ).all()

    total_allocated = sum(row.allocated_cents for row in allocations)
    total_spent = sum(row.spent_cents for row in allocations)
    total_pending = sum(row.pending_cents for row in allocations)
    total_remaining = sum(row.remaining_cents for row in allocations)
    unused_budget = total_remaining

    utilization = 0.0
    if total_allocated > 0:
        utilization = round((total_spent + total_pending) / total_allocated * 100, 1)

    pending_count = await db.scalar(
        select(func.count(PerkSelection.id)).where(
            PerkSelection.employer_id == org.id,
            PerkSelection.status == SelectionStatus.pending_approval,
        )
    )
    pending_count = int(pending_count or 0)

    employee_count = await db.scalar(
        select(func.count(EmployeeProfile.id)).where(
            EmployeeProfile.employer_id == org.id,
        )
    )
    employee_count = int(employee_count or 0)

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
        )
        .group_by(Perk.category)
        .order_by(func.count(PerkSelection.id).desc())
        .limit(5)
    )

    top_categories: list[CategoryInsight] = []
    for category, count, spent in category_rows.all():
        cat_value = category.value if hasattr(category, "value") else str(category)
        top_categories.append(
            CategoryInsight(
                category=cat_value,
                selection_count=int(count),
                spent_cents=int(spent or 0),
            )
        )

    if top_categories:
        lead = top_categories[0].category.replace("_", " ")
        insight_summary = (
            f"{lead.title()} is your team's most selected category this period "
            f"with {top_categories[0].selection_count} selection(s). "
        )
    else:
        insight_summary = (
            "No perk selections yet — encourage your team to explore the marketplace. "
        )

    if pending_count > 0:
        insight_summary += f"{pending_count} selection(s) awaiting your approval."
    elif utilization < 30 and total_allocated > 0:
        insight_summary += (
            f"Only {utilization:.0f}% of budget is used — "
            "consider promoting underused categories."
        )
    else:
        insight_summary += f"Budget utilization is at {utilization:.0f}%."

    return EmployerInsightsData(
        period=period,
        currency_code=currency_code,
        employee_count=employee_count,
        total_allocated_cents=total_allocated,
        total_spent_cents=total_spent,
        total_pending_cents=total_pending,
        total_remaining_cents=total_remaining,
        unused_budget_cents=unused_budget,
        utilization_pct=utilization,
        pending_approval_count=pending_count,
        top_categories=top_categories,
        allocated_formatted=format_money(
            total_allocated, currency_code=currency_code, locale=locale
        ),
        spent_formatted=format_money(total_spent, currency_code=currency_code, locale=locale),
        pending_formatted=format_money(
            total_pending, currency_code=currency_code, locale=locale
        ),
        remaining_formatted=format_money(
            total_remaining, currency_code=currency_code, locale=locale
        ),
        insight_summary=insight_summary.strip(),
    )
