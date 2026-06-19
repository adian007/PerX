"""Employer approval API schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ApprovalQueueEmployee(BaseModel):
    """Employee summary on an approval queue item."""

    model_config = ConfigDict(strict=True)

    id: str
    name: str
    department: str | None = None


class ApprovalQueuePerk(BaseModel):
    """Perk summary on an approval queue item."""

    model_config = ConfigDict(strict=True)

    id: str
    name: str
    category: str
    image_url: str | None = None


class ApprovalQueueItem(BaseModel):
    """Single row in GET /employer/approvals."""

    model_config = ConfigDict(strict=True)

    selection_id: str
    package_id: str | None = None
    employee: ApprovalQueueEmployee
    perk: ApprovalQueuePerk
    price_cents: int
    budget_remaining_after_cents: int
    selected_at: str


class ApproveResponseData(BaseModel):
    """POST /employer/approvals/{id}/approve response."""

    model_config = ConfigDict(strict=True)

    status: str
    notification_sent: bool
    approved_count: int = 1


class RejectRequest(BaseModel):
    """Body for POST /employer/approvals/{id}/reject."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)


class RejectResponseData(BaseModel):
    """POST /employer/approvals/{id}/reject response."""

    model_config = ConfigDict(strict=True)

    status: str
    notification_sent: bool
    rejected_count: int = 1


class BulkApproveRequest(BaseModel):
    """Body for POST /employer/approvals/bulk-approve."""

    model_config = ConfigDict(extra="forbid")

    selection_ids: list[uuid.UUID] = Field(min_length=1)


class BulkApproveResponseData(BaseModel):
    """POST /employer/approvals/bulk-approve response."""

    model_config = ConfigDict(strict=True)

    approved: int
    failed: int
