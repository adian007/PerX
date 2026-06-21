"""Receipt extraction via region detection and OCR parsing."""

from __future__ import annotations

from typing import Any

from app.pipelines.base import VisionPipeline
from app.utils.manifest import pipeline_override
from app.utils.receipt import analyze_receipt


class ReceiptPipeline(VisionPipeline):
    task_name = "receipt"

    def analyze(self, image_bgr: np.ndarray, payload: dict[str, Any]) -> dict[str, Any]:
        result = analyze_receipt(image_bgr)
        result["technique"] = "receipt-region-ocr-heuristics"

        override = pipeline_override(self.task_name)
        if override:
            result["custom_weights_configured"] = True
        return result
