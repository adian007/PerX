"""Simulated payment audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PaymentStatus

if TYPE_CHECKING:
    from app.models.employer import EmployerOrganization
    from app.models.provider import ProviderProfile
    from app.models.selection import PerkSelection


class Payment(Base):
    """Simulated payout record after selection approval (ADR-007)."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_cents >= 0", name="payments_amount_cents_check"),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="payments_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    perk_selection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("perk_selections.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employer_organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'ALL'"))
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False, length=20),
        nullable=False,
        server_default=text("'pending'"),
        index=True,
    )
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    perk_selection: Mapped["PerkSelection"] = relationship(back_populates="payments")
    provider: Mapped["ProviderProfile"] = relationship(back_populates="payments")
    employer: Mapped["EmployerOrganization"] = relationship(back_populates="payments")
