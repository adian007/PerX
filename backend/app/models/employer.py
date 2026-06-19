"""Employer organization extension table."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BudgetPeriod

if TYPE_CHECKING:
    from app.models.budget import BudgetAllocation
    from app.models.employee import EmployeeProfile
    from app.models.payment import Payment
    from app.models.selection import PerkSelection
    from app.models.user import User


class EmployerOrganization(Base):
    """Employer role extension — one per employer user."""

    __tablename__ = "employer_organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vat_number: Mapped[Optional[str]] = mapped_column(String(50))
    logo_url: Mapped[Optional[str]] = mapped_column(Text)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_city: Mapped[Optional[str]] = mapped_column(String(100))
    address_country: Mapped[str] = mapped_column(String(2), nullable=False, server_default=text("'IT'"))
    default_monthly_budget_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    default_currency_code: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'ALL'")
    )
    require_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    budget_period: Mapped[BudgetPeriod] = mapped_column(
        SAEnum(BudgetPeriod, name="budget_period", create_type=False),
        nullable=False,
        server_default=text("'monthly'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="employer_organization")
    employees: Mapped[list["EmployeeProfile"]] = relationship(back_populates="employer")
    budget_allocations: Mapped[list["BudgetAllocation"]] = relationship(back_populates="employer")
    perk_selections: Mapped[list["PerkSelection"]] = relationship(back_populates="employer")
    payments: Mapped[list["Payment"]] = relationship(back_populates="employer")
