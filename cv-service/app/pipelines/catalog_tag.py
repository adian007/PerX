"""Catalog tag suggestion from colors and optional OCR keywords."""

from __future__ import annotations

from typing import Any

from app.pipelines.base import VisionPipeline
from app.utils.colors import CATALOG_TAGS, catalog_scores_from_colors, catalog_scores_from_keywords
from app.utils.manifest import pipeline_override
from app.utils.ocr import extract_text


class CatalogTagPipeline(VisionPipeline):
    task_name = "catalog_tag"

    def analyze(self, image_bgr: np.ndarray, payload: dict[str, Any]) -> dict[str, Any]:
        color_scores = catalog_scores_from_colors(image_bgr)
        ocr = extract_text(image_bgr)
        keyword_scores = catalog_scores_from_keywords(ocr.get("text", ""))

        combined: dict[str, float] = {}
        for tag in CATALOG_TAGS:
            combined[tag] = color_scores.get(tag, 0.0) * 0.55 + keyword_scores.get(tag, 0.0) * 0.45

        ranked = sorted(combined.items(), key=lambda item: item[1], reverse=True)
        tags = [tag for tag, score in ranked[:3] if score > 0.2]
        if not tags:
            tags = [ranked[0][0]]

        category_hint = ranked[0][0]
        top_score = ranked[0][1]

        result: dict[str, Any] = {
            "tags": tags,
            "category_hint": category_hint,
            "score": round(min(0.98, top_score), 2),
            "signals": {
                "color_scores": {k: round(v, 3) for k, v in color_scores.items()},
                "keyword_scores": {k: round(v, 3) for k, v in keyword_scores.items()},
                "ocr_engine": ocr.get("engine"),
            },
            "technique": "color-heuristics+ocr-keywords",
        }

        override = pipeline_override(self.task_name)
        if override:
            result["custom_weights_configured"] = True
        return result
