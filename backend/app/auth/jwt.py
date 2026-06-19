"""JWT access token issue and decode (HS256)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings

REVOKED_JTI_PREFIX = "revoked_jti:"


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or validated."""


def create_access_token(*, user_id: uuid.UUID, role: str) -> tuple[str, str, datetime]:
    """Issue a 15-minute access token. Returns (token, jti, expires_at)."""

    settings = get_settings()
    jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token payload."""

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise TokenError("Invalid or expired token") from exc

    if not payload.get("sub") or not payload.get("jti") or not payload.get("role"):
        raise TokenError("Invalid token payload")

    return payload
