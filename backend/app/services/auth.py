"""Authentication business logic."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import REVOKED_JTI_PREFIX, create_access_token
from app.auth.passwords import hash_password, hash_token, verify_password, verify_token
from app.config import get_settings
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import ProviderStatus, UserRole
from app.models.provider import ProviderProfile
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    LoginResponseData,
    RefreshResponseData,
    RegisterRequest,
    RegisterResponseData,
    AuthUserResponse,
)
from app.utils.redis import RedisClient

ACCESS_TOKEN_SECONDS = 15 * 60


def _generate_invite_code() -> str:
    """Generate a human-readable employer invite code."""

    suffix = secrets.token_hex(2).upper()
    return f"PERX-{suffix}"


def _validate_registration(body: RegisterRequest) -> None:
    """Validate cross-field registration rules."""

    if body.role == UserRole.employee and not body.employer_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "employer_code is required for employee registration",
                "details": {"field": "employer_code"},
            },
        )


async def register_user(db: AsyncSession, body: RegisterRequest) -> RegisterResponseData:
    """Create a new user and role extension row."""

    _validate_registration(body)

    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_ALREADY_EXISTS",
                "message": "An account with this email already exists",
                "details": {},
            },
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    if body.role == UserRole.employer:
        db.add(
            EmployerOrganization(
                user_id=user.id,
                organization_name=f"{body.email.split('@')[0].title()} Organization",
                invite_code=_generate_invite_code(),
                contact_name="Primary Contact",
            )
        )
    elif body.role == UserRole.provider:
        db.add(
            ProviderProfile(
                user_id=user.id,
                company_name=f"{body.email.split('@')[0].title()} Services",
                status=ProviderStatus.pending_review,
            )
        )
    elif body.role == UserRole.employee:
        employer = await db.scalar(
            select(EmployerOrganization).where(EmployerOrganization.invite_code == body.employer_code)
        )
        if employer is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_EMPLOYER_CODE",
                    "message": "Employer invite code is invalid",
                    "details": {},
                },
            )
        local_part = body.email.split("@")[0]
        db.add(
            EmployeeProfile(
                user_id=user.id,
                employer_id=employer.id,
                first_name=local_part.title(),
                last_name="User",
            )
        )

    await db.flush()
    return RegisterResponseData(user_id=str(user.id), role=user.role)


async def _issue_tokens(db: AsyncSession, user: User) -> tuple[str, str, datetime]:
    """Create access + refresh tokens and persist refresh hash."""

    settings = get_settings()
    access_token, _, _ = create_access_token(user_id=user.id, role=user.role.value)
    refresh_plain = secrets.token_urlsafe(32)
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_plain),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_row)
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    return access_token, refresh_plain, refresh_row.expires_at


async def login_user(db: AsyncSession, *, email: str, password: str) -> LoginResponseData:
    """Verify credentials and issue tokens."""

    user = await db.scalar(
        select(User)
        .options(selectinload(User.employee_profile))
        .where(User.email == email)
    )
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password",
                "details": {},
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCOUNT_INACTIVE",
                "message": "Account is inactive",
                "details": {},
            },
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "message": "Verify your email to continue",
                "details": {},
            },
        )

    access_token, refresh_token, _ = await _issue_tokens(db, user)
    onboarding_completed = False
    if user.employee_profile is not None:
        onboarding_completed = user.employee_profile.onboarding_completed

    return LoginResponseData(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_SECONDS,
        user=AuthUserResponse(
            id=str(user.id),
            email=user.email,
            role=user.role,
            onboarding_completed=onboarding_completed,
        ),
    )


async def _find_refresh_token(db: AsyncSession, plain_token: str) -> RefreshToken | None:
    """Locate a refresh token row by bcrypt hash comparison."""

    rows = await db.scalars(
        select(RefreshToken).where(
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    for row in rows:
        if verify_token(plain_token, row.token_hash):
            return row
    return None


async def refresh_tokens(db: AsyncSession, *, refresh_token: str) -> RefreshResponseData:
    """Rotate refresh token (single-use) and issue a new access token."""

    row = await _find_refresh_token(db, refresh_token)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_REFRESH_TOKEN",
                "message": "Refresh token is invalid",
                "details": {},
            },
        )

    user = await db.scalar(select(User).where(User.id == row.user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_REVOKED",
                "message": "Refresh token is no longer valid",
                "details": {},
            },
        )

    row.is_revoked = True
    access_token, new_refresh, _ = await _issue_tokens(db, user)
    return RefreshResponseData(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=ACCESS_TOKEN_SECONDS,
    )


async def logout_user(
    db: AsyncSession,
    redis: RedisClient,
    *,
    user: User,
    access_token: str,
    refresh_token: str,
) -> None:
    """Revoke access jti in Redis and invalidate refresh token."""

    from app.auth.jwt import decode_access_token, TokenError

    try:
        payload = decode_access_token(access_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": str(exc),
                "details": {},
            },
        ) from exc

    if payload["sub"] != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Token subject mismatch",
                "details": {},
            },
        )

    jti = payload["jti"]
    exp = payload.get("exp")
    ttl_seconds = ACCESS_TOKEN_SECONDS
    if isinstance(exp, (int, float)):
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        ttl_seconds = max(remaining, 1)

    await redis.setex(f"{REVOKED_JTI_PREFIX}{jti}", ttl_seconds, "1")

    row = await _find_refresh_token(db, refresh_token)
    if row is not None and row.user_id == user.id:
        row.is_revoked = True
