"""Base pipeline contract for cv-service tasks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from app.utils.image import decode_payload_image


class VisionPipeline(ABC):
    """Abstract interface for a CV task pipeline."""

    task_name: str

    def load_image(self, payload: dict[str, Any]) -> np.ndarray:
        return decode_payload_image(payload)

    @abstractmethod
    def analyze(self, image_bgr: np.ndarray, payload: dict[str, Any]) -> dict[str, Any]:
        """Run task-specific analysis on a decoded BGR image."""

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            image_bgr = self.load_image(payload)
        except ValueError as exc:
            return {"error": str(exc), "success": False}
        return self.analyze(image_bgr, payload)
