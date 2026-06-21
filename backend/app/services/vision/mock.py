"""Deterministic local fallback results for vision tasks."""

from __future__ import annotations

import hashlib
from typing import Any


def _seed(task: str, payload: dict[str, Any]) -> int:
    source = f"{task}|{payload.get('image_url', '')}|{len(payload.get('image_base64') or '')}|{sorted((payload.get('metadata') or {}).items())}"
    return int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:12], 16)


def _mock_meta() -> dict[str, Any]:
    return {
        "mock": True,
        "warning": "Shërbimi CV nuk është aktiv. Ky rezultat nuk vjen nga imazhi yt.",
    }


def deterministic_result(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    seed = _seed(task, payload)
    meta = _mock_meta()
    if task == "lifestyle":
        labels = ["active", "family", "minimalist", "traveler", "wellness"]
        return {
            **meta,
            "primary_label": labels[seed % len(labels)],
            "confidence": round(0.7 + (seed % 20) / 100, 2),
        }
    if task == "receipt":
        total = 1000 + (seed % 9000)
        return {
            **meta,
            "merchant": f"MockMerchant-{seed % 97}",
            "currency": "ALL",
            "total_cents": total,
        }
    if task == "ocr":
        return {**meta, "text": f"Mock OCR #{seed % 10000}", "language": "en"}
    if task == "catalog_tag":
        tags = ["fitness", "travel", "wellness", "food", "education"]
        return {
            **meta,
            "tags": [tags[seed % len(tags)], tags[(seed + 1) % len(tags)]],
            "score": 0.88,
        }
    return {
        **meta,
        "matches": [
            {"item_id": f"perk-{100 + (seed % 25)}", "score": 0.93},
            {"item_id": f"perk-{200 + (seed % 25)}", "score": 0.89},
        ],
    }

