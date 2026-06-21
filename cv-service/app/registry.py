"""Pipeline registry for cv-service."""

from __future__ import annotations

from app.pipelines.base import VisionPipeline
from app.pipelines.catalog_tag import CatalogTagPipeline
from app.pipelines.lifestyle import LifestylePipeline
from app.pipelines.ocr import OcrPipeline
from app.pipelines.receipt import ReceiptPipeline
from app.pipelines.visual_search import VisualSearchPipeline

PIPELINE_REGISTRY: dict[str, VisionPipeline] = {
    "lifestyle": LifestylePipeline(),
    "receipt": ReceiptPipeline(),
    "ocr": OcrPipeline(),
    "catalog_tag": CatalogTagPipeline(),
    "visual_search": VisualSearchPipeline(),
}

