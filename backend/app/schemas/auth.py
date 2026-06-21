"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import UserRole
from app.schemas.validators import normalize_auth_email

PASSWORD_MIN_LENGTH = 8
EMPLOYER_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")


class RegisterRequest(BaseModel):
    """Body for POST /api/v1/auth/register."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role: UserRole
    employer_code: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_auth_email(value)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < PASSWORD_MIN_LENGTH:
            raise ValueError("Password must be at least 8 characters")
        if value.isdigit() or value.isalpha():
            raise ValueError("Password must include letters and numbers")
        return value

    @field_validator("employer_code")
    @classmethod
    def validate_employer_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not EMPLOYER_CODE_PATTERN.match(normalized):
            raise ValueError("Invalid employer code format")
        return normalized


class LoginRequest(BaseModel):
    """Body for POST /api/v1/auth/login."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_auth_email(value)


class RefreshRequest(BaseModel):
    """Body for POST /api/v1/auth/refresh."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=32, max_length=256)


class LogoutRequest(BaseModel):
    """Body for POST /api/v1/auth/logout."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=32, max_length=256)


class AuthUserResponse(BaseModel):
    """User summary returned on login."""

    model_config = ConfigDict(strict=True)

    id: str
    email: str
    role: UserRole
    onboarding_completed: bool = False


class TokenPairResponse(BaseModel):
    """Access and refresh token pair."""

    model_config = ConfigDict(strict=True)

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class LoginResponseData(TokenPairResponse):
    """Login response including user profile."""

    user: AuthUserResponse


class RefreshResponseData(TokenPairResponse):
    """Refresh response — tokens only."""


class RegisterResponseData(BaseModel):
    """Registration confirmation."""

    model_config = ConfigDict(strict=True)

    user_id: str
    role: UserRole
    message: str = "Verify your email to continue."

class PushSubscriptionRequest(BaseModel):
    """Body for POST /api/v1/auth/push-subscription."""

    model_config = ConfigDict(extra="forbid")

    push_endpoint: str = Field(min_length=1)
    push_p256dh: str = Field(min_length=1)
    push_auth: str = Field(min_length=1)

