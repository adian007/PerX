"""Notification repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType
from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    """Insert an in-app notification row."""

    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        data=data or {},
    )
    db.add(notification)
    await db.flush()
    return notification


async def list_user_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list[Notification]:
    """List notifications for a user, newest first."""

    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    result = await db.scalars(stmt)
    return list(result.all())


async def get_notification_for_user(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Load a notification scoped to the owning user."""

    return await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )


async def mark_notification_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Mark a single notification as read."""

    notification = await get_notification_for_user(db, notification_id, user_id)
    if notification is None:
        return None
    notification.is_read = True
    await db.flush()
    return notification


async def mark_all_notifications_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Mark all unread notifications as read; return count updated."""

    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return result.rowcount or 0
