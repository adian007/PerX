"""Async Redis client with in-memory fallback for tests."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncGenerator
from typing import Any

from app.config import get_settings

RATE_LIMIT_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class InMemoryRedis:
    """Minimal async Redis stand-in for tests and offline development."""

    def __init__(self) -> None:
        self._strings: dict[str, tuple[int, float | None]] = {}
        self._sets: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def _purge_expired(self, key: str) -> None:
        entry = self._strings.get(key)
        if entry is None:
            return
        _, expires_at = entry
        if expires_at is not None and expires_at <= time.monotonic():
            del self._strings[key]

    async def incr(self, key: str) -> int:
        async with self._lock:
            await self._purge_expired(key)
            current, expires_at = self._strings.get(key, (0, None))
            current += 1
            self._strings[key] = (current, expires_at)
            return current

    async def expire(self, key: str, seconds: int) -> bool:
        async with self._lock:
            if key not in self._strings:
                return False
            count, _ = self._strings[key]
            self._strings[key] = (count, time.monotonic() + seconds)
            return True

    async def eval(self, script: str, numkeys: int, key: str, ttl_seconds: str) -> int:
        async with self._lock:
            await self._purge_expired(key)
            current, expires_at = self._strings.get(key, (0, None))
            current += 1
            if current == 1:
                expires_at = time.monotonic() + int(ttl_seconds)
            self._strings[key] = (current, expires_at)
            return current

    async def sadd(self, key: str, member: str) -> int:
        async with self._lock:
            members = self._sets.setdefault(key, set())
            if member in members:
                return 0
            members.add(member)
            return 1

    async def sismember(self, key: str, member: str) -> bool:
        async with self._lock:
            return member in self._sets.get(key, set())

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        async with self._lock:
            self._strings[key] = (int(value) if value.isdigit() else 0, time.monotonic() + seconds)
            return True

    async def get(self, key: str) -> str | None:
        async with self._lock:
            await self._purge_expired(key)
            entry = self._strings.get(key)
            if entry is None:
                return None
            count, _ = entry
            return str(count)

    async def delete(self, key: str) -> int:
        async with self._lock:
            removed = 0
            if key in self._strings:
                del self._strings[key]
                removed += 1
            if key in self._sets:
                del self._sets[key]
                removed += 1
            return removed

    async def flushdb(self) -> bool:
        async with self._lock:
            self._strings.clear()
            self._sets.clear()
            return True

    async def aclose(self) -> None:
        return None


class RedisClient:
    """Wrapper around real Redis or the in-memory fallback."""

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    async def eval(self, script: str, numkeys: int, key: str, ttl_seconds: str) -> int:
        return int(await self._backend.eval(script, numkeys, key, ttl_seconds))

    async def get(self, key: str) -> str | None:
        return await self._backend.get(key)

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        return bool(await self._backend.setex(key, seconds, value))

    async def sadd(self, key: str, member: str) -> int:
        return int(await self._backend.sadd(key, member))

    async def sismember(self, key: str, member: str) -> bool:
        return bool(await self._backend.sismember(key, member))

    async def delete(self, key: str) -> int:
        return int(await self._backend.delete(key))

    async def flushdb(self) -> bool:
        return bool(await self._backend.flushdb())

    async def aclose(self) -> None:
        close = getattr(self._backend, "aclose", None)
        if close is not None:
            await close()


_redis_client: RedisClient | None = None


async def _connect_redis() -> RedisClient:
    settings = get_settings()
    if settings.redis_use_memory or os.getenv("REDIS_USE_MEMORY", "").lower() in {"1", "true", "yes"}:
        return RedisClient(InMemoryRedis())

    try:
        import redis.asyncio as aioredis

        raw = aioredis.from_url(settings.redis_url, decode_responses=True)
        await raw.ping()
        return RedisClient(raw)
    except Exception:
        return RedisClient(InMemoryRedis())


async def get_redis_client() -> RedisClient:
    """Return the shared Redis client, initializing on first use."""

    global _redis_client
    if _redis_client is None:
        _redis_client = await _connect_redis()
    return _redis_client


async def get_redis() -> AsyncGenerator[RedisClient, None]:
    """Yield the shared Redis client (in-memory when Redis is unavailable)."""

    yield await get_redis_client()


async def reset_redis_for_tests() -> None:
    """Reset the global client — used between tests."""

    global _redis_client
    if _redis_client is not None:
        await _redis_client.flushdb()
        await _redis_client.aclose()
    _redis_client = None


async def init_redis() -> RedisClient:
    """Initialize Redis on application startup."""

    global _redis_client
    _redis_client = await _connect_redis()
    return _redis_client


async def close_redis() -> None:
    """Close Redis on application shutdown."""

    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
