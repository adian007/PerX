"""Authentication routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.employer import EmployerOrganization
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponseData,
    LogoutRequest,
    PushSubscriptionRequest,
    RefreshRequest,
    RefreshResponseData,
    RegisterRequest,
    RegisterResponseData,
)
from app.schemas.recommendations import ApiEnvelope
from app.services.auth import (
    login_user,
    logout_user,
    refresh_tokens,
    register_push_subscription,
    register_user,
)
from app.utils.envelope import envelope
from app.utils.redis import RedisClient, get_redis

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=True)


@router.get("/demo-info", response_model=ApiEnvelope)
async def demo_info(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Return demo login hints when ALLOW_DEMO_MODE is enabled."""

    settings = get_settings()
    if not settings.allow_demo_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": "Not found",
                "details": {},
            },
        )

    employer = await db.scalar(select(EmployerOrganization).limit(1))
    employee = await db.scalar(
        select(User)
        .where(User.email.like("%mira.warm%"))
        .order_by(User.created_at.asc())
    )
    return envelope(
        {
            "employer_code": employer.invite_code if employer else "ACME-DEMO",
            "demo_email": employee.email if employee else "mira.warm@example.com",
            "demo_password": "Demo1234",
        }
    )


@router.post("/register", response_model=ApiEnvelope, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Register a new user account."""

    data = await register_user(db, body)
    return envelope(RegisterResponseData.model_validate(data.model_dump()).model_dump())


@router.post("/login", response_model=ApiEnvelope)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Authenticate and issue access/refresh tokens."""

    data = await login_user(db, email=body.email, password=body.password)
    return envelope(LoginResponseData.model_validate(data.model_dump()).model_dump())


@router.post("/refresh", response_model=ApiEnvelope)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Rotate refresh token and issue a new access token pair."""

    data = await refresh_tokens(db, refresh_token=body.refresh_token)
    return envelope(RefreshResponseData.model_validate(data.model_dump()).model_dump())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> Response:
    """Revoke the current access token jti and refresh token."""

    await logout_user(
        db,
        redis,
        user=current_user,
        access_token=credentials.credentials,
        refresh_token=body.refresh_token,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/push-subscription", status_code=status.HTTP_204_NO_CONTENT)
async def push_subscription(
    body: PushSubscriptionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Register or update the authenticated user's Web Push subscription."""

    await register_push_subscription(db, current_user, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
