"""Perk schemas split by role — employees never see provider_cost_cents."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class PerkEmployeeRead(BaseModel):
    """Employee-facing perk shape — provider_cost_cents is structurally absent."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    category: str
    employee_price_cents: int
    currency_code: str = "ALL"
    image_url: str | None = None
    short_description: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_featured: bool = False


class PerkProviderRead(BaseModel):
    """Provider/admin-facing perk shape including internal cost fields."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    category: str
    employee_price_cents: int
    provider_cost_cents: int
    currency_code: str = "ALL"
    image_url: str | None = None
    short_description: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True
