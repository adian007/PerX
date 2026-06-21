"""OCR helpers with graceful Tesseract fallback."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

import cv2
import numpy as np

from app.utils.image import grayscale

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def tesseract_available() -> bool:
    try:
        import pytesseract  # noqa: PLC0415

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def preprocess_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
    gray = grayscale(image_bgr)
    gray = cv2.bilateralFilter(gray, 5, 50, 50)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_text_tesseract(image_bgr: np.ndarray) -> dict[str, Any]:
    import pytesseract  # noqa: PLC0415

    pil_image = _bgr_to_pil(image_bgr)
    text = pytesseract.image_to_string(pil_image).strip()
    data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)

    blocks: list[dict[str, Any]] = []
    n = len(data.get("text", []))
    for i in range(n):
        token = (data["text"][i] or "").strip()
        if not token:
            continue
        conf_raw = data["conf"][i]
        try:
            conf = float(conf_raw) / 100.0
        except (TypeError, ValueError):
            conf = 0.0
        if conf <= 0:
            continue
        blocks.append({"text": token, "confidence": round(conf, 2)})

    lang = "en"
    if text:
        try:
            osd = pytesseract.image_to_osd(pil_image).strip()
            lang_match = re.search(r"Script:\s*(\w+)", osd)
            if lang_match:
                lang = lang_match.group(1).lower()[:2] or "en"
        except Exception:
            lang = "en"

    return {
        "text": text,
        "language": lang,
        "blocks": blocks,
        "engine": "tesseract",
        "ocr_available": True,
    }


def extract_text_fallback(image_bgr: np.ndarray) -> dict[str, Any]:
    """OpenCV contour heuristic when Tesseract is unavailable."""

    thresh = preprocess_for_ocr(image_bgr)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    text_like = 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < 80:
            continue
        aspect = w / float(max(h, 1))
        if 0.15 < aspect < 12 and h < image_bgr.shape[0] * 0.2:
            text_like += 1

    hint = f"[ocr-unavailable: detected ~{text_like} text-like regions]"
    return {
        "text": hint if text_like else "",
        "language": "en",
        "blocks": [],
        "engine": "opencv-heuristic",
        "ocr_available": False,
        "text_region_count": text_like,
    }


def extract_text(image_bgr: np.ndarray) -> dict[str, Any]:
    if tesseract_available():
        try:
            return extract_text_tesseract(image_bgr)
        except Exception as exc:
            logger.warning("Tesseract OCR failed, using fallback: %s", exc)
    return extract_text_fallback(image_bgr)


def _bgr_to_pil(image_bgr: np.ndarray):
    from PIL import Image  # noqa: PLC0415

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)
