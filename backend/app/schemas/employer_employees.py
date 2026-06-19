"""Employer employee roster schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EmployerEmployeeSummary(BaseModel):
    """Single employee row for GET /employer/employees."""

    model_config = ConfigDict(strict=True)

    id: str
    name: str
    department: str | None = None
    email: str
    budget_allocated_cents: int
    budget_spent_cents: int
    budget_pending_cents: int
    budget_remaining_cents: int
    budget_utilization_pct: float
    pending_approvals_count: int
    active_selections_count: int


class EmployerEmployeeListData(BaseModel):
    """Paginated employee list wrapper."""

    model_config = ConfigDict(strict=True)

    employees: list[EmployerEmployeeSummary]
    total: int
    page: int
    per_page: int
