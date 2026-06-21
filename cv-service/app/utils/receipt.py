"""Receipt region detection and text parsing heuristics."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import cv2
import numpy as np

from app.utils.image import aspect_ratio, grayscale
from app.utils.ocr import extract_text

AMOUNT_RE = re.compile(
    r"(?:total|amount|sum|subtotal|tax)?\s*[:=]?\s*(?:ALL|USD|EUR)?\s*(\d{1,6}[.,]\d{2})",
    re.IGNORECASE,
)
SIMPLE_AMOUNT_RE = re.compile(r"(\d{1,6}[.,]\d{2})")
DATE_RE = re.compile(
    r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}[/.-]\d{1,2}[/.-]\d{1,2})",
)


def detect_receipt_region(image_bgr: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Find a bright, tall receipt-like region or return the full frame."""

    gray = grayscale(image_bgr)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_score = 0.0
    img_area = image_bgr.shape[0] * image_bgr.shape[1]

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < img_area * 0.05:
            continue
        roi = gray[y : y + h, x : x + w]
        brightness = float(roi.mean()) / 255.0
        tall = h / float(max(w, 1))
        score = brightness * 0.5 + min(tall / 3.0, 1.0) * 0.3 + (area / img_area) * 0.2
        if score > best_score:
            best_score = score
            best = (x, y, w, h)

    meta: dict[str, Any] = {
        "receipt_like": best is not None and best_score > 0.35,
        "region_score": round(best_score, 3),
        "aspect_ratio": round(aspect_ratio(image_bgr), 3),
    }

    if best is None:
        return image_bgr, meta

    x, y, w, h = best
    pad = 4
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(image_bgr.shape[1], x + w + pad)
    y1 = min(image_bgr.shape[0], y + h + pad)
    meta["bbox"] = [x0, y0, x1 - x0, y1 - y0]
    return image_bgr[y0:y1, x0:x1], meta


def _amount_to_cents(value: str) -> int:
    normalized = value.replace(",", ".")
    return int(round(float(normalized) * 100))


def parse_receipt_text(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    merchant = lines[0][:80] if lines else "Unknown Merchant"

    amounts: list[int] = []
    for match in AMOUNT_RE.finditer(text):
        amounts.append(_amount_to_cents(match.group(1)))
    if not amounts:
        for match in SIMPLE_AMOUNT_RE.finditer(text):
            amounts.append(_amount_to_cents(match.group(1)))

    total_cents = amounts[-1] if amounts else 0
    subtotal_cents = amounts[0] if amounts else total_cents
    tax_cents = max(total_cents - subtotal_cents, 0) if len(amounts) >= 2 else 0

    date_match = DATE_RE.search(text)
    receipt_date = None
    if date_match:
        raw = date_match.group(1)
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                receipt_date = datetime.strptime(raw, fmt).date().isoformat()
                break
            except ValueError:
                continue
        if receipt_date is None:
            receipt_date = raw

    line_items: list[dict[str, Any]] = []
    for line in lines[1:6]:
        item_amount = SIMPLE_AMOUNT_RE.search(line)
        if not item_amount:
            continue
        name = SIMPLE_AMOUNT_RE.sub("", line).strip(" -:\t")
        if not name:
            continue
        line_items.append(
            {
                "name": name[:120],
                "qty": 1,
                "price_cents": _amount_to_cents(item_amount.group(1)),
            }
        )

    return {
        "merchant": merchant,
        "currency": "ALL",
        "subtotal_cents": subtotal_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "line_items": line_items,
        "receipt_date": receipt_date,
        "raw_text_preview": text[:500] if text else "",
    }


def analyze_receipt(image_bgr: np.ndarray) -> dict[str, Any]:
    region, region_meta = detect_receipt_region(image_bgr)
    ocr = extract_text(region)
    parsed = parse_receipt_text(ocr.get("text", ""))

    if not parsed["total_cents"] and region_meta.get("receipt_like"):
        parsed["confidence_note"] = "receipt-like region detected; OCR may need tesseract for amounts"

    return {
        **parsed,
        "detection": region_meta,
        "ocr_engine": ocr.get("engine"),
        "ocr_available": ocr.get("ocr_available", False),
    }
