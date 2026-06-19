"""Marketplace perks and interaction log."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import InteractionType, PerkCategory

if TYPE_CHECKING:
    from app.models.employee import EmployeeProfile, EmployeeWishlist
    from app.models.package import PackageItem
    from app.models.provider import ProviderProfile, ProviderRating
    from app.models.selection import PerkSelection


class Perk(Base):
    """Marketplace perk listing."""

    __tablename__ = "perks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[Optional[str]] = mapped_column(String(500))
    category: Mapped[PerkCategory] = mapped_column(
        SAEnum(PerkCategory, name="perk_category", create_type=False), nullable=False, index=True
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    employee_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # NEVER expose provider_cost_cents in employee-facing Pydantic schemas.
    provider_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'ALL'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    max_monthly_per_employee: Mapped[Optional[int]] = mapped_column(Integer)
    stock_limit: Mapped[Optional[int]] = mapped_column(Integer)
    available_from: Mapped[Optional[date]] = mapped_column(Date)
    available_until: Mapped[Optional[date]] = mapped_column(Date)
    intensity_level: Mapped[Optional[int]] = mapped_column(Integer)
    time_commitment_hours: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    is_digital: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_family_friendly: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    minimum_commitment_months: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("1"))
    popularity_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), server_default=text("0"))
    quality_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), server_default=text("0"))
    trend_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), server_default=text("0"))
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    provider: Mapped["ProviderProfile"] = relationship(back_populates="perks")
    perk_selections: Mapped[list["PerkSelection"]] = relationship(back_populates="perk")
    perk_interactions: Mapped[list["PerkInteraction"]] = relationship(back_populates="perk")
    wishlist_entries: Mapped[list["EmployeeWishlist"]] = relationship(back_populates="perk")
    package_items: Mapped[list["PackageItem"]] = relationship(back_populates="perk")
    ratings: Mapped[list["ProviderRating"]] = relationship(back_populates="perk")


class PerkInteraction(Base):
    """Append-only recommender training log — never update or delete rows in app code."""

    __tablename__ = "perk_interactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_profiles.id"), nullable=False, index=True
    )
    perk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perks.id"), nullable=False, index=True
    )
    interaction_type: Mapped[InteractionType] = mapped_column(
        SAEnum(InteractionType, name="interaction_type", create_type=False),
        nullable=False,
        index=True,
    )
    recommendation_rank: Mapped[Optional[int]] = mapped_column(Integer)
    page_context: Mapped[Optional[str]] = mapped_column(String(50))
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    device_type: Mapped[Optional[str]] = mapped_column(String(20))
    is_offline: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    employee: Mapped["EmployeeProfile"] = relationship(back_populates="perk_interactions")
    perk: Mapped["Perk"] = relationship(back_populates="perk_interactions")
