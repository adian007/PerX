"""Visual search embedding pipeline."""

from __future__ import annotations

from typing import Any

from app.pipelines.base import VisionPipeline
from app.utils.embedding import visual_search_result
from app.utils.manifest import pipeline_override


class VisualSearchPipeline(VisionPipeline):
    task_name = "visual_search"

    def analyze(self, image_bgr: np.ndarray, payload: dict[str, Any]) -> dict[str, Any]:
        result = visual_search_result(image_bgr)
        result["technique"] = "histogram-perceptual-hash-embedding"

        override = pipeline_override(self.task_name)
        if override:
            result["custom_weights_configured"] = True
            result["note"] = "custom encoder/index from manifest not loaded; using built-in embedding"
        return result
