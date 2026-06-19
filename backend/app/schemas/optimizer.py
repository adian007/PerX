"""Plan optimizer request/response schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class OptimizePlanRequest(BaseModel):
    """Body for POST /selections/optimize-plan."""

    model_config = ConfigDict(extra="forbid")

    perk_ids: list[uuid.UUID] = Field(min_length=1)


class OptimizePlanApprovedPerk(BaseModel):
    """Single perk row in optimizer output."""

    model_config = ConfigDict(strict=True)

    perk_id: uuid.UUID
    name: str
    price_cents: int
    score: float
    included: bool
    exclusion_reason: str | None = None


class OptimizePlanResponseData(BaseModel):
    """Knapsack optimization result."""

    model_config = ConfigDict(strict=True)

    run_id: str
    status: str
    solver_time_ms: int
    budget_available_cents: int
    approved_perks: list[OptimizePlanApprovedPerk]
    total_cost_cents: int
    total_score: float
    explanation: str


class ConfirmPlanRequest(BaseModel):
    """Empty body for confirm endpoint."""

    model_config = ConfigDict(extra="forbid")


class ConfirmPlanResponseData(BaseModel):
    """Confirm optimizer run success."""

    model_config = ConfigDict(strict=True)

    selection_ids: list[str]
    budget_remaining_cents: int
    budget_remaining_formatted: str
