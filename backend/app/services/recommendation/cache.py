"""Recommendation score cache — Redis with in-memory fallback."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import get_settings
from app.utils.redis import InMemoryRedis, RedisClient, get_redis_client

RECOMMENDATION_CACHE_TTL_SECONDS = 86400
RECOMMENDATION_KEY_PREFIX = "recs:"


@dataclass(frozen=True)
class CachedRecommendationPayload:
    """A cached recommendation response with metadata."""

    payload: dict[str, Any]
    cached_at: float


class RecommendationCache(Protocol):
    """Cache protocol matching ADR-006 key ``recs:{employee_id}:scores``."""

    async def get(self, employee_id: str) -> CachedRecommendationPayload | None:
        """Return cached payload if present and not expired."""

    async def set(
        self,
        employee_id: str,
        payload: dict[str, Any],
        ttl_seconds: int = RECOMMENDATION_CACHE_TTL_SECONDS,
    ) -> None:
        """Store a recommendation payload with TTL."""

    async def delete(self, employee_id: str) -> None:
        """Remove a cached payload."""


@dataclass
class _CacheEntry:
    payload: dict[str, Any]
    cached_at: float
    expires_at: float


class InMemoryRecommendationCache:
    """In-memory cache used for tests and when Redis is unavailable."""

    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}

    async def get(self, employee_id: str) -> CachedRecommendationPayload | None:
        entry = self._entries.get(employee_id)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._entries[employee_id]
            return None
        return CachedRecommendationPayload(
            payload=entry.payload,
            cached_at=entry.cached_at,
        )

    async def set(
        self,
        employee_id: str,
        payload: dict[str, Any],
        ttl_seconds: int = RECOMMENDATION_CACHE_TTL_SECONDS,
    ) -> None:
        now = time.monotonic()
        self._entries[employee_id] = _CacheEntry(
            payload=payload,
            cached_at=now,
            expires_at=now + ttl_seconds,
        )

    async def delete(self, employee_id: str) -> None:
        self._entries.pop(employee_id, None)


class RedisRecommendationCache:
    """Redis-backed recommendation cache using ADR-006 key prefix."""

    def __init__(self, redis: RedisClient) -> None:
        self._redis = redis

    def _key(self, cache_key: str) -> str:
        return f"{RECOMMENDATION_KEY_PREFIX}{cache_key}"

    async def get(self, employee_id: str) -> CachedRecommendationPayload | None:
        raw = await self._redis.get(self._key(employee_id))
        if raw is None:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            await self._redis.delete(self._key(employee_id))
            return None
        payload = parsed.get("payload")
        cached_at = parsed.get("cached_at")
        if not isinstance(payload, dict) or not isinstance(cached_at, (int, float)):
            await self._redis.delete(self._key(employee_id))
            return None
        return CachedRecommendationPayload(payload=payload, cached_at=float(cached_at))

    async def set(
        self,
        employee_id: str,
        payload: dict[str, Any],
        ttl_seconds: int = RECOMMENDATION_CACHE_TTL_SECONDS,
    ) -> None:
        envelope = json.dumps({"payload": payload, "cached_at": time.monotonic()})
        await self._redis.setex(self._key(employee_id), ttl_seconds, envelope)

    async def delete(self, employee_id: str) -> None:
        await self._redis.delete(self._key(employee_id))


def _use_memory_backend() -> bool:
    settings = get_settings()
    return settings.redis_use_memory or os.getenv("REDIS_USE_MEMORY", "").lower() in {
        "1",
        "true",
        "yes",
    }


recommendation_cache: RecommendationCache = InMemoryRecommendationCache()


async def init_recommendation_cache() -> RecommendationCache:
    """Select Redis or in-memory cache based on runtime connectivity."""

    global recommendation_cache
    if _use_memory_backend():
        recommendation_cache = InMemoryRecommendationCache()
        return recommendation_cache

    redis = await get_redis_client()
    if isinstance(redis._backend, InMemoryRedis):
        recommendation_cache = InMemoryRecommendationCache()
    else:
        recommendation_cache = RedisRecommendationCache(redis)
    return recommendation_cache
