"""Synthetic test images — no external fixtures."""

from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def solid_bgr(color_bgr: tuple[int, int, int], size: tuple[int, int] = (320, 240)) -> np.ndarray:
    image = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    image[:, :] = color_bgr
    return image


def solid_rgb(color_rgb: tuple[int, int, int], size: tuple[int, int] = (320, 240)) -> np.ndarray:
    b, g, r = color_rgb[2], color_rgb[1], color_rgb[0]
    return solid_bgr((b, g, r), size=size)


def receipt_image() -> np.ndarray:
    image = np.full((500, 300, 3), 245, dtype=np.uint8)
    pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    lines = [
        "Cafe PerX",
        "Espresso        2.50",
        "Croissant       3.20",
        "Subtotal        5.70",
        "Tax             1.03",
        "TOTAL           6.73",
        "Date 20/06/2026",
    ]
    y = 30
    for line in lines:
        draw.text((20, y), line, fill=(0, 0, 0))
        y += 28
    rgb = np.asarray(pil)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def text_document_image(text: str = "PerX Benefits OCR Test") -> np.ndarray:
    pil = Image.new("RGB", (400, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(pil)
    draw.text((20, 40), text, fill=(0, 0, 0))
    rgb = np.asarray(pil)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def bgr_to_base64(image_bgr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", image_bgr)
    assert ok
    return base64.b64encode(buf.tobytes()).decode("ascii")
