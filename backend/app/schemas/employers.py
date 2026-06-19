"""Employer API response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EmployerOrganizationData(BaseModel):
    """GET /employer/organization response data."""

    model_config = ConfigDict(strict=True)

    id: str
    organization_name: str
    logo_url: str | None = None
    contact_name: str
    default_monthly_budget_cents: int
    default_currency_code: str
    require_approval: bool
    invite_code: str
