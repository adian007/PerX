"""In-app notifications and optional web push (log-only stub when VAPID unset)."""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification import (
    count_user_notifications,
    create_notification,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.schemas.notifications import NotificationItem, ReadAllResponseData
from app.services.access_control import assert_role
from app.models.enums import UserRole

logger = logging.getLogger(__name__)


async def notify_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    """Create an in-DB notification row."""

    return await create_notification(
        db,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data,
    )


async def send_push_if_configured(user: User, title: str, body: str, data: dict | None = None) -> bool:
    """Attempt web push when VAPID keys and subscription exist; otherwise log only."""

    settings = get_settings()
    if not settings.vapid_private_key or not user.push_endpoint:
        logger.info(
            "Push stub (VAPID unset or no subscription): user=%s title=%s body=%s data=%s",
            user.id,
            title,
            body,
            data or {},
        )
        return False

    subscription_info = {
        "endpoint": user.push_endpoint,
        "keys": {"p256dh": user.push_p256dh, "auth": user.push_auth},
    }
    try:
        from pywebpush import WebPushException, webpush

        webpush(
            subscription_info=subscription_info,
            data=json.dumps({"title": title, "body": body, "data": data or {}}),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_claims_email},
        )
        return True
    except WebPushException as exc:
        logger.warning("Push notification failed for user %s: %s", user.id, exc)
        return False
    except ImportError:
        logger.info(
            "pywebpush unavailable; push stub for user=%s title=%s",
            user.id,
            title,
        )
        return False


async def list_my_notifications(
    db: AsyncSession,
    user: User,
    *,
    unread_only: bool = False,
    limit: int = 20,
    page: int = 1,
) -> tuple[list[NotificationItem], int]:
    """List notifications for the authenticated user with total count."""

    assert_role(user, {UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin})
    offset = (page - 1) * limit
    total = await count_user_notifications(db, user.id, unread_only=unread_only)
    rows = await list_user_notifications(
        db,
        user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    items = [
        NotificationItem(
            id=str(row.id),
            type=row.type.value,
            title=row.title,
            body=row.body,
            data=row.data or {},
            is_read=row.is_read,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
    return items, total


async def mark_one_read(
    db: AsyncSession,
    user: User,
    notification_id: uuid.UUID,
) -> NotificationItem:
    """Mark a single notification as read."""

    from fastapi import HTTPException, status

    notification = await mark_notification_read(db, notification_id, user.id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOTIFICATION_NOT_FOUND",
                "message": "Notification not found",
                "details": {},
            },
        )
    return NotificationItem(
        id=str(notification.id),
        type=notification.type.value,
        title=notification.title,
        body=notification.body,
        data=notification.data or {},
        is_read=notification.is_read,
        created_at=notification.created_at.isoformat(),
    )


async def mark_all_read(db: AsyncSession, user: User) -> ReadAllResponseData:
    """Mark all notifications as read for the current user."""

    assert_role(user, {UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin})
    updated = await mark_all_notifications_read(db, user.id)
    return ReadAllResponseData(updated=updated)
