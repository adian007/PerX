"""Knapsack optimizer audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import EmployeeProfile


class OptimizerRun(Base):
    """Audit record for plan_optimize knapsack runs."""

    __tablename__ = "optimizer_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_profiles.id"), nullable=False
    )
    wishlist_perk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    wishlist_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    budget_available_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_perk_ids: Mapped[Optional[list[uuid.UUID]]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    excluded_perk_ids: Mapped[Optional[list[uuid.UUID]]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    total_cost_cents: Mapped[Optional[int]] = mapped_column(Integer)
    total_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    solver_status: Mapped[Optional[str]] = mapped_column(String(50))
    solver_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    employee: Mapped["EmployeeProfile"] = relationship(back_populates="optimizer_runs")
