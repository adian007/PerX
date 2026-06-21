"""General document OCR pipeline."""

from __future__ import annotations

from typing import Any

from app.pipelines.base import VisionPipeline
from app.utils.manifest import pipeline_override
from app.utils.ocr import extract_text, preprocess_for_ocr, tesseract_available


class OcrPipeline(VisionPipeline):
    task_name = "ocr"

    def analyze(self, image_bgr: np.ndarray, payload: dict[str, Any]) -> dict[str, Any]:
        preprocessed = preprocess_for_ocr(image_bgr)
        ocr = extract_text(image_bgr)

        result: dict[str, Any] = {
            "text": ocr.get("text", ""),
            "language": ocr.get("language", "en"),
            "blocks": ocr.get("blocks", []),
            "ocr_available": ocr.get("ocr_available", tesseract_available()),
            "engine": ocr.get("engine", "unknown"),
            "technique": "tesseract" if ocr.get("ocr_available") else "opencv-heuristic-fallback",
            "preprocessed_shape": list(preprocessed.shape),
        }

        override = pipeline_override(self.task_name)
        if override:
            result["custom_weights_configured"] = True
        return result
