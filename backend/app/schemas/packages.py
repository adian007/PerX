"""Package catalog API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PackagePerkItem(BaseModel):
    """Perk line inside a package listing."""

    model_config = ConfigDict(strict=True)

    perk_id: str
    name: str
    category: str
    employee_price_cents: int
    provider_name: str


class PackageListItem(BaseModel):
    """Single package in GET /packages."""

    model_config = ConfigDict(strict=True)

    id: str
    name: str
    description: str | None = None
    category: str | None = None
    total_price_cents: int
    currency_code: str
    items: list[PackagePerkItem]


class PackageSelectionResponseData(BaseModel):
    """POST /selections/package/{package_id} response."""

    model_config = ConfigDict(strict=True)

    package_id: str
    selection_ids: list[str]
    status: str
    total_price_cents: int
    budget_remaining_cents: int
    message: str
