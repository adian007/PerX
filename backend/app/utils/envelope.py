"""Shared API response envelope."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def envelope(data: Any, request_id: str = "local-demo") -> dict[str, Any]:
    """Return the standard PerX API response envelope."""

    return {
        "data": data,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
        },
    }
