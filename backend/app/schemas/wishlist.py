"""Wishlist request/response schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class WishlistAddResponseData(BaseModel):
    """POST /me/wishlist/{perk_id} success payload."""

    model_config = ConfigDict(strict=True)

    added: bool
    perk_id: uuid.UUID
