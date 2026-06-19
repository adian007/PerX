"""Notification routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.notifications import MarkReadResponseData, ReadAllResponseData
from app.schemas.recommendations import ApiEnvelope
from app.services.notifications import list_my_notifications, mark_all_read, mark_one_read
from app.utils.envelope import envelope

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=ApiEnvelope)
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin)),
    ],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
    unread_only: bool = Query(default=False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """List notifications for the authenticated user."""

    items = await list_my_notifications(
        db,
        current_user,
        unread_only=unread_only,
        limit=per_page,
        page=page,
    )
    payload = [item.model_dump() for item in items]
    response = envelope(payload)
    response["meta"].update(
        {"total": len(payload), "page": page, "per_page": per_page, "pages": 1}
    )
    return response


@router.post("/notifications/{notification_id}/read", response_model=ApiEnvelope)
async def mark_notification_read_route(
    notification_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin)),
    ],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Mark a single notification as read."""

    item = await mark_one_read(db, current_user, notification_id)
    return envelope(
        MarkReadResponseData(id=item.id, is_read=item.is_read).model_dump()
    )


@router.post("/notifications/read-all", response_model=ApiEnvelope)
async def mark_all_notifications_read_route(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin)),
    ],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Mark all notifications as read."""

    data = await mark_all_read(db, current_user)
    return envelope(ReadAllResponseData.model_validate(data.model_dump()).model_dump())
