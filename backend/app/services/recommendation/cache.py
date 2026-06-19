"""Recommendation score cache — in-memory stub for Redis integration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

RECOMMENDATION_CACHE_TTL_SECONDS = 86400


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
    """In-memory cache used for local demos until Redis is wired."""

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


recommendation_cache = InMemoryRecommendationCache()
