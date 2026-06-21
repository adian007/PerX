"""Gamification models — journey, quiz, achievements, reviews."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
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

if TYPE_CHECKING:
    from app.models.perk import Perk
    from app.models.user import User


class Achievement(Base):
    """Static achievement catalog."""

    __tablename__ = "achievements"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    interactive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    goal: Mapped[Optional[int]] = mapped_column(Integer)

    employee_unlocks: Mapped[list["EmployeeAchievement"]] = relationship(back_populates="achievement")


class EmployeeGamification(Base):
    """Core XP/points/streak state per user."""

    __tablename__ = "employee_gamification"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    points: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    class_label: Mapped[str] = mapped_column(String(100), nullable=False, server_default=text("'I ri'"))
    marathoner_miles: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_active_date: Mapped[Optional[date]] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="gamification")


class JourneyProgress(Base):
    """Completed journey path nodes by category."""

    __tablename__ = "journey_progress"
    __table_args__ = (UniqueConstraint("user_id", "category"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'completed'"))
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QuizScore(Base):
    """Best quiz score per category."""

    __tablename__ = "quiz_scores"
    __table_args__ = (UniqueConstraint("user_id", "category"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EmployeeAchievement(Base):
    """Unlocked achievements for an employee."""

    __tablename__ = "employee_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    achievement_slug: Mapped[str] = mapped_column(
        String(50), ForeignKey("achievements.slug", ondelete="CASCADE"), nullable=False
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    achievement: Mapped["Achievement"] = relationship(back_populates="employee_unlocks")


class EmployeeReview(Base):
    """Perk reviews submitted by employees."""

    __tablename__ = "employee_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "perk_id"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_employee_reviews_rating"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    perk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perks.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    perk: Mapped["Perk"] = relationship(back_populates="employee_reviews")
