"""Deterministic mock helpers for stable CV stubs."""

from __future__ import annotations

import hashlib
from typing import Any


def deterministic_seed(task: str, payload: dict[str, Any]) -> int:
    """Generate stable seed from task + relevant payload fields."""

    image_url = payload.get("image_url") or ""
    image_b64 = payload.get("image_base64") or ""
    metadata = payload.get("metadata") or {}
    source = f"{task}|{image_url}|{len(image_b64)}|{sorted(metadata.items())}"
    return int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:12], 16)

