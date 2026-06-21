"""Optional manifest.yaml loader for custom model overrides."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


@lru_cache(maxsize=1)
def load_manifest(models_dir: str | None = None) -> dict[str, Any] | None:
    root = Path(models_dir) if models_dir else DEFAULT_MODELS_DIR
    manifest_path = root / "manifest.yaml"
    if not manifest_path.is_file():
        return None

    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        logger.info("PyYAML not installed; ignoring manifest at %s", manifest_path)
        return None

    try:
        with manifest_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except Exception as exc:
        logger.warning("Failed to read manifest %s: %s", manifest_path, exc)
        return None

    if not isinstance(data, dict) or not data.get("pipelines"):
        return None
    return data


def pipeline_override(task: str, models_dir: str | None = None) -> dict[str, Any] | None:
    manifest = load_manifest(models_dir)
    if not manifest:
        return None
    pipelines = manifest.get("pipelines") or {}
    override = pipelines.get(task)
    return override if isinstance(override, dict) else None
