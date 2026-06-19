"""Provider profile and ratings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ProviderStatus

if TYPE_CHECKING:
    from app.models.employee import EmployeeProfile
    from app.models.payment import Payment
    from app.models.perk import Perk
    from app.models.selection import PerkSelection
    from app.models.user import User


class ProviderProfile(Base):
    """Provider role extension — one per provider user."""

    __tablename__ = "provider_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    logo_url: Mapped[Optional[str]] = mapped_column(Text)
    website_url: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ProviderStatus] = mapped_column(
        SAEnum(ProviderStatus, name="provider_status", create_type=False),
        nullable=False,
        server_default=text("'pending_review'"),
        index=True,
    )
    available_countries: Mapped[list[str]] = mapped_column(
        ARRAY(String(2)), nullable=False, server_default=text("'{IT}'")
    )
    available_cities: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    is_nationwide: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_remote: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    avg_rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), server_default=text("0"))
    total_redemptions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_perks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, server_default=text("15.00"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="provider_profile")
    perks: Mapped[list["Perk"]] = relationship(back_populates="provider")
    ratings: Mapped[list["ProviderRating"]] = relationship(back_populates="provider")
    payments: Mapped[list["Payment"]] = relationship(back_populates="provider")


class ProviderRating(Base):
    """One rating per employee per selection."""

    __tablename__ = "provider_ratings"
    __table_args__ = (UniqueConstraint("employee_id", "selection_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_profiles.id"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id"), nullable=False, index=True
    )
    perk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perks.id"), nullable=False, index=True
    )
    selection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perk_selections.id"), nullable=False
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    rated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    employee: Mapped["EmployeeProfile"] = relationship(back_populates="provider_ratings")
    provider: Mapped["ProviderProfile"] = relationship(back_populates="ratings")
    perk: Mapped["Perk"] = relationship(back_populates="ratings")
    selection: Mapped["PerkSelection"] = relationship(back_populates="rating")
