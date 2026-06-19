"""Budget allocation ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Computed, DateTime, ForeignKey, Integer, SmallInteger, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import EmployeeProfile
    from app.models.employer import EmployerOrganization
    from app.models.selection import PerkSelection


class BudgetAllocation(Base):
    """Per-employee budget for a given period."""

    __tablename__ = "budget_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employer_organizations.id"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_profiles.id"), nullable=False, index=True
    )
    period_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    period_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    allocated_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    spent_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    pending_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    remaining_cents: Mapped[int] = mapped_column(
        Integer,
        Computed("allocated_cents - spent_cents - pending_cents", persisted=True),
        nullable=False,
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'ALL'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    employer: Mapped["EmployerOrganization"] = relationship(back_populates="budget_allocations")
    employee: Mapped["EmployeeProfile"] = relationship(back_populates="budget_allocations")
    perk_selections: Mapped[list["PerkSelection"]] = relationship(back_populates="budget_allocation")
