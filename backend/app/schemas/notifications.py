"""Notification API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NotificationItem(BaseModel):
    """Single notification in list responses."""

    model_config = ConfigDict(strict=True)

    id: str
    type: str
    title: str
    body: str
    data: dict
    is_read: bool
    created_at: str


class MarkReadResponseData(BaseModel):
    """POST /notifications/{id}/read response."""

    model_config = ConfigDict(strict=True)

    id: str
    is_read: bool


class ReadAllResponseData(BaseModel):
    """POST /notifications/read-all response."""

    model_config = ConfigDict(strict=True)

    updated: int
