"""Lifestyle classification from color and scene heuristics."""

from __future__ import annotations

from typing import Any

from app.pipelines.base import VisionPipeline
from app.utils.colors import color_stats, dominant_colors, rank_lifestyle_labels
from app.utils.manifest import pipeline_override


class LifestylePipeline(VisionPipeline):
    task_name = "lifestyle"

    def analyze(self, image_bgr: np.ndarray, payload: dict[str, Any]) -> dict[str, Any]:
        ranked = rank_lifestyle_labels(image_bgr)
        primary, primary_score = ranked[0]
        secondary = [label for label, _ in ranked[1:3]]

        stats = color_stats(image_bgr)
        colors = dominant_colors(image_bgr, k=3)

        result: dict[str, Any] = {
            "primary_label": primary,
            "confidence": round(min(0.95, primary_score), 2),
            "secondary_labels": secondary,
            "scene_hints": {
                "brightness": round(stats["brightness"], 3),
                "saturation": round(stats["saturation"], 3),
                "warmth": round(stats["warmth"], 3),
                "dominant_colors_rgb": colors,
            },
            "technique": "color-scene-heuristics",
        }

        override = pipeline_override(self.task_name)
        if override:
            result["custom_weights_configured"] = True
        return result
