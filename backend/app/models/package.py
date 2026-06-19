"""Multi-provider package bundles."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.perk import Perk
    from app.models.selection import PerkSelection
    from app.models.user import User


class Package(Base):
    """Curated or employee-built bundle spanning multiple perks/providers."""

    __tablename__ = "packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    is_curated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    total_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'ALL'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    created_by_user: Mapped[Optional["User"]] = relationship(back_populates="packages_created")
    items: Mapped[list["PackageItem"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )
    perk_selections: Mapped[list["PerkSelection"]] = relationship(back_populates="package")


class PackageItem(Base):
    """Line item linking a package to a perk."""

    __tablename__ = "package_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    perk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("perks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    package: Mapped["Package"] = relationship(back_populates="items")
    perk: Mapped["Perk"] = relationship(back_populates="package_items")
