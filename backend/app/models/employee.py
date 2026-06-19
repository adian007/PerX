"""Employee profile and wishlist models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PerkCategory

if TYPE_CHECKING:
    from app.models.budget import BudgetAllocation
    from app.models.employer import EmployerOrganization
    from app.models.optimizer import OptimizerRun
    from app.models.perk import Perk, PerkInteraction
    from app.models.provider import ProviderRating
    from app.models.selection import PerkSelection
    from app.models.user import User


class EmployeeProfile(Base):
    """Employee role extension — one per employee user."""

    __tablename__ = "employee_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employer_organizations.id"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    job_title: Mapped[Optional[str]] = mapped_column(String(150))
    hire_date: Mapped[Optional[date]] = mapped_column(Date)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), index=True
    )
    lifestyle_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    preferred_categories: Mapped[Optional[list[PerkCategory]]] = mapped_column(
        ARRAY(SAEnum(PerkCategory, name="perk_category", create_type=False)),
        server_default=text("'{}'"),
    )
    budget_sensitivity: Mapped[Optional[str]] = mapped_column(String(20), server_default=text("'medium'"))
    wellness_priority: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("5"))
    family_situation: Mapped[Optional[str]] = mapped_column(String(20))
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    recommender_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'cold_start'"), index=True
    )
    affinity_vector: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    affinity_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    welcome_explanation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="employee_profile")
    employer: Mapped["EmployerOrganization"] = relationship(back_populates="employees")
    budget_allocations: Mapped[list["BudgetAllocation"]] = relationship(back_populates="employee")
    perk_selections: Mapped[list["PerkSelection"]] = relationship(back_populates="employee")
    perk_interactions: Mapped[list["PerkInteraction"]] = relationship(back_populates="employee")
    wishlist_items: Mapped[list["EmployeeWishlist"]] = relationship(back_populates="employee")
    optimizer_runs: Mapped[list["OptimizerRun"]] = relationship(back_populates="employee")
    provider_ratings: Mapped[list["ProviderRating"]] = relationship(back_populates="employee")


class EmployeeWishlist(Base):
    """Pre-optimization wishlist entries."""

    __tablename__ = "employee_wishlists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee_profiles.id"), nullable=False
    )
    perk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("perks.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    employee: Mapped["EmployeeProfile"] = relationship(back_populates="wishlist_items")
    perk: Mapped["Perk"] = relationship(back_populates="wishlist_entries")
