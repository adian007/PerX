"""HTTP client adapter for optional external cv-service."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.services.vision.mock import deterministic_result


async def analyze_with_cv_service(task: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Return task result and source marker."""

    settings = get_settings()
    if not settings.cv_enabled:
        return deterministic_result(task, payload), "backend-mock"

    timeout = httpx.Timeout(settings.cv_request_timeout_seconds)
    headers: dict[str, str] = {}
    if settings.cv_internal_key:
        headers["X-CV-Internal-Key"] = settings.cv_internal_key
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{settings.cv_service_url.rstrip('/')}/analyze",
                json={"task": task, **payload},
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
            return body.get("result", {}), "cv-service"
        except Exception:
            # Keep API non-blocking even when cv-service is unavailable.
            return deterministic_result(task, payload), "backend-fallback"

