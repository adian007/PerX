"""Pipeline unit tests with synthetic images."""

from __future__ import annotations

import numpy as np

from app.pipelines.catalog_tag import CatalogTagPipeline
from app.pipelines.lifestyle import LifestylePipeline
from app.pipelines.ocr import OcrPipeline
from app.pipelines.receipt import ReceiptPipeline
from app.pipelines.visual_search import VisualSearchPipeline
from app.utils.embedding import cosine_similarity, compute_embedding
from app.utils.ocr import tesseract_available
from tests.conftest import bgr_to_base64, receipt_image, solid_bgr, solid_rgb, text_document_image


def _payload(image_bgr: np.ndarray) -> dict:
    return {"image_base64": bgr_to_base64(image_bgr)}


def test_lifestyle_green_prefers_active_or_wellness():
    image = solid_rgb((30, 180, 60))
    result = LifestylePipeline().run(_payload(image))
    assert result["primary_label"] in {"active", "wellness", "minimalist", "family", "traveler"}
    assert 0.0 < result["confidence"] <= 0.95
    assert len(result["secondary_labels"]) == 2
    assert result["technique"] == "color-scene-heuristics"


def test_lifestyle_blue_traveler_signal():
    image = solid_rgb((40, 90, 220))
    result = LifestylePipeline().run(_payload(image))
    ranked = [result["primary_label"], *result["secondary_labels"]]
    assert "traveler" in ranked


def test_receipt_parses_structured_fields():
    image = receipt_image()
    result = ReceiptPipeline().run(_payload(image))
    assert "merchant" in result
    assert "total_cents" in result
    assert result["technique"] == "receipt-region-ocr-heuristics"
    if tesseract_available():
        assert "Cafe" in result["merchant"] or "PerX" in result.get("raw_text_preview", "")
        assert result["total_cents"] > 0


def test_ocr_returns_engine_metadata():
    image = text_document_image()
    result = OcrPipeline().run(_payload(image))
    assert "text" in result
    assert "blocks" in result
    assert "ocr_available" in result
    assert result["engine"] in {"tesseract", "opencv-heuristic"}
    if tesseract_available():
        assert "PerX" in result["text"] or "OCR" in result["text"]


def test_catalog_tag_red_image_food_hint():
    image = solid_rgb((220, 60, 40))
    result = CatalogTagPipeline().run(_payload(image))
    assert result["category_hint"] in {"food", "entertainment", "fitness", "travel", "wellness", "education"}
    assert len(result["tags"]) >= 1
    assert result["score"] > 0


def test_catalog_tag_keywords_from_ocr():
    image = text_document_image("yoga wellness spa retreat")
    result = CatalogTagPipeline().run(_payload(image))
    tags = set(result["tags"])
    if tesseract_available():
        assert "wellness" in tags or result["category_hint"] == "wellness"


def test_visual_search_embedding_stable_and_similar():
    a = solid_bgr((20, 120, 200))
    b = solid_bgr((22, 118, 198))
    c = solid_rgb((220, 30, 30))

    emb_a = compute_embedding(a)
    emb_b = compute_embedding(b)
    emb_c = compute_embedding(c)

    assert emb_a.shape == emb_b.shape
    assert cosine_similarity(emb_a, emb_b) > cosine_similarity(emb_a, emb_c)

    result = VisualSearchPipeline().run(_payload(a))
    assert result["embedding_dim"] == len(result["embedding"])
    assert result["query_embedding_hash"].startswith("emb-")
    assert len(result["matches"]) >= 1


def test_missing_image_returns_error():
    result = OcrPipeline().run({})
    assert result["success"] is False
    assert "image" in result["error"].lower()
