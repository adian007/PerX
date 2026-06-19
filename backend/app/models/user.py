"""Core auth identity and refresh tokens."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.employee import EmployeeProfile
    from app.models.employer import EmployerOrganization
    from app.models.notification import Notification
    from app.models.package import Package
    from app.models.provider import ProviderProfile
    from app.models.selection import PerkSelection


class User(Base):
    """Shared auth identity; extends to exactly one role table except admin."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=False), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    push_endpoint: Mapped[Optional[str]] = mapped_column(Text)
    push_p256dh: Mapped[Optional[str]] = mapped_column(Text)
    push_auth: Mapped[Optional[str]] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'sq-AL'"))
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'UTC'"))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    employee_profile: Mapped[Optional["EmployeeProfile"]] = relationship(
        back_populates="user", uselist=False
    )
    employer_organization: Mapped[Optional["EmployerOrganization"]] = relationship(
        back_populates="user", uselist=False
    )
    provider_profile: Mapped[Optional["ProviderProfile"]] = relationship(
        back_populates="user", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    packages_created: Mapped[list["Package"]] = relationship(back_populates="created_by_user")
    selections_approved: Mapped[list["PerkSelection"]] = relationship(
        back_populates="approved_by_user", foreign_keys="PerkSelection.approved_by"
    )


class RefreshToken(Base):
    """JWT refresh token storage."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
