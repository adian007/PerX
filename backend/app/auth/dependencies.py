"""FastAPI auth dependencies — JWT extraction and RBAC guards."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import REVOKED_JTI_PREFIX, TokenError, decode_access_token
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.services.access_control import assert_role
from app.utils.redis import RedisClient, get_redis

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> User:
    """Extract Bearer token, decode JWT, check revocation, load active user."""

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": str(exc),
                "details": {},
            },
        ) from exc

    jti = payload["jti"]
    if await redis.get(f"{REVOKED_JTI_PREFIX}{jti}") is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_REVOKED",
                "message": "Access token has been revoked",
                "details": {},
            },
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid token subject",
                "details": {},
            },
        ) from exc

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "User not found or inactive",
                "details": {},
            },
        )

    return user


def require_role(*roles: UserRole | str) -> Callable[..., User]:
    """FastAPI dependency factory enforcing one of the given roles."""

    allowed = {UserRole(role) if isinstance(role, str) else role for role in roles}

    async def _require_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        assert_role(current_user, allowed)
        return current_user

    return _require_role
