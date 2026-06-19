from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class QuickAddRequest(BaseModel):
    """Body for POST /selections/quick-add."""

    model_config = ConfigDict(extra="forbid")

    perk_id: uuid.UUID


class QuickAddResponseData(BaseModel):
    """Quick-add success payload."""

    model_config = ConfigDict(strict=True)

    selection_id: str
    status: str
    budget_remaining_cents: int
    budget_remaining_formatted: str
    message: str


class SelectionListItem(BaseModel):
    """Single row in GET /me/selections."""

    model_config = ConfigDict(strict=True)

    id: str
    status: str
    price_cents_snapshot: int
    selected_at: str
    perk: dict
