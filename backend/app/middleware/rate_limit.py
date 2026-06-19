"""Redis-backed rate limiting with in-memory fallback."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_optional_current_user
from app.models.user import User
from app.utils.redis import RATE_LIMIT_LUA, RedisClient, get_redis

RATE_LIMIT_WINDOW_SECONDS = 60

ENDPOINT_LIMITS: dict[str, int] = {
    "POST:/api/v1/auth/login": 5,
    "POST:/api/v1/auth/register": 3,
    "GET:/api/v1/recommendations": 30,
    "POST:/api/v1/selections/quick-add": 10,
    "POST:/api/v1/selections/optimize-plan": 5,
}

DEFAULT_LIMIT = 60

AUTH_RATE_LIMIT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
}


def normalize_path(path: str) -> str:
    """Normalize UUID path segments for limit lookup."""

    return re.sub(r"/[0-9a-fA-F-]{36}", "/{id}", path)


def limit_for_request(method: str, path: str) -> int:
    """Return the configured limit for a method/path pair."""

    normalized = normalize_path(path)
    return ENDPOINT_LIMITS.get(f"{method}:{normalized}", DEFAULT_LIMIT)


def client_ip(request: Request) -> str:
    """Resolve the client IP, honoring X-Forwarded-For when present."""

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def rate_limit_key(request: Request, *, user_id: str | None = None) -> tuple[str, str]:
    """Build the Redis key and endpoint identifier for rate limiting."""

    method = request.method.upper()
    path = normalize_path(request.url.path)
    endpoint = f"{method}:{path}"

    if path in AUTH_RATE_LIMIT_PATHS:
        return f"ratelimit:ip:{client_ip(request)}:{endpoint}", endpoint

    if user_id:
        return f"ratelimit:user:{user_id}:{endpoint}", endpoint

    return f"ratelimit:ip:{client_ip(request)}:{endpoint}", endpoint


async def check_rate_limit(
    request: Request,
    redis: RedisClient,
    *,
    user_id: str | None = None,
) -> tuple[int, int]:
    """Increment the counter and return (count, limit). Raises 429 when exceeded."""

    key, endpoint = rate_limit_key(request, user_id=user_id)
    limit = ENDPOINT_LIMITS.get(endpoint, DEFAULT_LIMIT)
    count = await redis.eval_rate_limit(key, str(RATE_LIMIT_WINDOW_SECONDS))
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests",
                "details": {"limit": limit, "window_seconds": RATE_LIMIT_WINDOW_SECONDS},
            },
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )
    return count, limit


async def enforce_auth_rate_limit(
    request: Request,
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> None:
    """Rate-limit unauthenticated auth endpoints by client IP."""

    if request.url.path in AUTH_RATE_LIMIT_PATHS:
        await check_rate_limit(request, redis)


async def enforce_user_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> None:
    """Rate-limit authenticated requests per user_id."""

    await check_rate_limit(request, redis, user_id=str(current_user.id))


async def enforce_optional_rate_limit(
    request: Request,
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> None:
    """Rate-limit by user when authenticated, otherwise by client IP."""

    user_id = str(current_user.id) if current_user is not None else None
    await check_rate_limit(request, redis, user_id=user_id)
