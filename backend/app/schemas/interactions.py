"""Interaction logging request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InteractionTypeLiteral = Literal[
    "view",
    "click",
    "detail_open",
    "add_to_wishlist",
    "remove_from_wishlist",
    "select",
    "reject",
    "redeem",
]


class InteractionCreateRequest(BaseModel):
    """Body for POST /interactions."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    perk_id: uuid.UUID
    interaction_type: InteractionTypeLiteral = Field(alias="type")
    recommendation_rank: int | None = Field(default=None, ge=1)
    page_context: str | None = Field(default=None, max_length=50)
    session_id: str | None = Field(default=None, max_length=100)
    occurred_at: datetime | None = None


class InteractionBatchRequest(BaseModel):
    """Body for POST /interactions/batch."""

    model_config = ConfigDict(extra="forbid")

    events: list[InteractionCreateRequest] = Field(min_length=1, max_length=100)


class InteractionLoggedResponse(BaseModel):
    """Single interaction log success."""

    model_config = ConfigDict(strict=True)

    logged: bool = True


class InteractionBatchResponse(BaseModel):
    """Batch interaction log result."""

    model_config = ConfigDict(strict=True)

    accepted: int
    rejected: int
