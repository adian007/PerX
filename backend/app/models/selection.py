"""Perk selection (marketplace transaction)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SelectionStatus

if TYPE_CHECKING:
    from app.models.budget import BudgetAllocation
    from app.models.employee import EmployeeProfile
    from app.models.employer import EmployerOrganization
    from app.models.package import Package
    from app.models.payment import Payment
    from app.models.perk import Perk
    from app.models.provider import ProviderRating
    from app.models.user import User


class PerkSelection(Base):
    """Employee perk selection awaiting or past employer approval."""

    __tablename__ = "perk_selections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_profiles.id"), nullable=False, index=True
    )
    perk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perks.id"), nullable=False, index=True
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employer_organizations.id"), nullable=False, index=True
    )
    budget_allocation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_allocations.id"), nullable=False
    )
    package_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[SelectionStatus] = mapped_column(
        SAEnum(SelectionStatus, name="selection_status", create_type=False),
        nullable=False,
        server_default=text("'pending_approval'"),
        index=True,
    )
    price_cents_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'ALL'"))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    redeemed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    redemption_code: Mapped[Optional[str]] = mapped_column(String(100))
    was_optimized: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    optimization_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    was_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    recommendation_rank: Mapped[Optional[int]] = mapped_column(Integer)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped["EmployeeProfile"] = relationship(back_populates="perk_selections")
    perk: Mapped["Perk"] = relationship(back_populates="perk_selections")
    employer: Mapped["EmployerOrganization"] = relationship(back_populates="perk_selections")
    budget_allocation: Mapped["BudgetAllocation"] = relationship(back_populates="perk_selections")
    package: Mapped[Optional["Package"]] = relationship(back_populates="perk_selections")
    approved_by_user: Mapped[Optional["User"]] = relationship(
        back_populates="selections_approved", foreign_keys=[approved_by]
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="perk_selection")
    rating: Mapped[Optional["ProviderRating"]] = relationship(
        back_populates="selection", uselist=False
    )
