"""Employee API response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr


class EmployerSummary(BaseModel):
    """Nested employer summary on employee profile."""

    model_config = ConfigDict(strict=True)

    id: str
    organization_name: str
    logo_url: str | None = None


class EmployeeMeData(BaseModel):
    """GET /me response data."""

    model_config = ConfigDict(strict=True)

    id: str
    email: EmailStr
    first_name: str
    last_name: str
    avatar_url: str | None = None
    department: str | None = None
    job_title: str | None = None
    onboarding_completed: bool
    recommender_mode: str
    interaction_count: int
    locale: str = "sq-AL"
    currency_code: str = "ALL"
    employer: EmployerSummary


class BudgetSummaryData(BaseModel):
    """GET /me/budget response data."""

    model_config = ConfigDict(strict=True)

    period: str
    allocated_cents: int
    spent_cents: int
    pending_cents: int
    remaining_cents: int
    currency_code: str = "ALL"
    utilization_pct: float = 0.0
    allocated_formatted: str = ""
    spent_formatted: str = ""
    pending_formatted: str = ""
    remaining_formatted: str = ""
