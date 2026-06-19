"""Employer employee roster with budget summaries."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.enums import SelectionStatus
from app.models.selection import PerkSelection
from app.models.user import User
from app.repositories.budget import current_period
from app.schemas.employer_employees import EmployerEmployeeListData, EmployerEmployeeSummary
from app.services.access_control import require_employer_org


async def list_employer_employees(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    per_page: int = 50,
    department: str | None = None,
    search: str | None = None,
) -> EmployerEmployeeListData:
    """List employees in the employer org with current-period budget summaries."""

    org = await require_employer_org(db, user)
    year, month = current_period()

    filters = [EmployeeProfile.employer_id == org.id]
    if department:
        filters.append(EmployeeProfile.department == department)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                EmployeeProfile.first_name.ilike(pattern),
                EmployeeProfile.last_name.ilike(pattern),
            )
        )

    total = await db.scalar(select(func.count(EmployeeProfile.id)).where(*filters))
    total = int(total or 0)

    offset = (page - 1) * per_page
    employees = (
        await db.scalars(
            select(EmployeeProfile)
            .options(selectinload(EmployeeProfile.user))
            .where(*filters)
            .order_by(EmployeeProfile.last_name, EmployeeProfile.first_name)
            .offset(offset)
            .limit(per_page)
        )
    ).all()

    summaries: list[EmployerEmployeeSummary] = []
    for employee in employees:
        allocation = await db.scalar(
            select(BudgetAllocation).where(
                BudgetAllocation.employee_id == employee.id,
                BudgetAllocation.period_year == year,
                BudgetAllocation.period_month == month,
            )
        )

        allocated = allocation.allocated_cents if allocation else 0
        spent = allocation.spent_cents if allocation else 0
        pending_budget = allocation.pending_cents if allocation else 0
        remaining = allocation.remaining_cents if allocation else 0

        utilization = 0.0
        if allocated > 0:
            utilization = round((spent + pending_budget) / allocated * 100, 1)

        pending_approvals = await db.scalar(
            select(func.count(PerkSelection.id)).where(
                PerkSelection.employee_id == employee.id,
                PerkSelection.status == SelectionStatus.pending_approval,
            )
        )
        active_selections = await db.scalar(
            select(func.count(PerkSelection.id)).where(
                PerkSelection.employee_id == employee.id,
                PerkSelection.status.in_(
                    [SelectionStatus.pending_approval, SelectionStatus.approved]
                ),
            )
        )

        summaries.append(
            EmployerEmployeeSummary(
                id=str(employee.id),
                name=f"{employee.first_name} {employee.last_name}".strip(),
                department=employee.department,
                email=employee.user.email if employee.user else "",
                budget_allocated_cents=allocated,
                budget_spent_cents=spent,
                budget_pending_cents=pending_budget,
                budget_remaining_cents=remaining,
                budget_utilization_pct=utilization,
                pending_approvals_count=int(pending_approvals or 0),
                active_selections_count=int(active_selections or 0),
            )
        )

    return EmployerEmployeeListData(
        employees=summaries,
        total=total,
        page=page,
        per_page=per_page,
    )
