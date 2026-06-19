"""WebSocket realtime event gateway."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import REVOKED_JTI_PREFIX, TokenError, decode_access_token
from app.database import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.services.access_control import require_employee_profile, require_employer_org
from app.services.websocket_gateway import get_websocket_gateway
from app.utils.redis import get_redis_client

router = APIRouter(prefix="/ws", tags=["websocket"])


async def _authenticate_ws_token(token: str) -> User:
    """Validate JWT from query string and load the active user."""

    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise PermissionError(str(exc)) from exc

    redis = await get_redis_client()
    jti = payload["jti"]
    if await redis.get(f"{REVOKED_JTI_PREFIX}{jti}") is not None:
        raise PermissionError("Token revoked")

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise PermissionError("Invalid token subject") from exc

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.id == user_id))
        if user is None or not user.is_active:
            raise PermissionError("User not found or inactive")
        return user


@router.websocket("/employee/{employee_id}")
async def employee_websocket(
    websocket: WebSocket,
    employee_id: uuid.UUID,
    token: Annotated[str, Query()],
) -> None:
    """Employee channel — JWT via ?token=; only own employee_id allowed."""

    gateway = get_websocket_gateway()
    try:
        user = await _authenticate_ws_token(token)
        async with AsyncSessionLocal() as db:
            profile = await require_employee_profile(db, user)
            if profile.id != employee_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
    except PermissionError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await gateway.connect_employee(str(employee_id), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        gateway.disconnect_employee(str(employee_id), websocket)


@router.websocket("/employer/{employer_id}")
async def employer_websocket(
    websocket: WebSocket,
    employer_id: uuid.UUID,
    token: Annotated[str, Query()],
) -> None:
    """Employer channel — JWT via ?token=; only own organization allowed."""

    gateway = get_websocket_gateway()
    try:
        user = await _authenticate_ws_token(token)
        async with AsyncSessionLocal() as db:
            org = await require_employer_org(db, user)
            if org.id != employer_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
    except PermissionError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await gateway.connect_employer(str(employer_id), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        gateway.disconnect_employer(str(employer_id), websocket)
