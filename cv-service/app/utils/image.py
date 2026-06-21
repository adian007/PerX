"""Image decode, resize, and preprocess helpers."""

from __future__ import annotations

import base64
import io
from typing import Any

import cv2
import numpy as np
from PIL import Image

DEFAULT_MAX_DIM = 1024


def _strip_data_url(value: str) -> str:
    if "," in value and value.strip().lower().startswith("data:"):
        return value.split(",", 1)[1]
    return value


def image_from_base64(value: str) -> Image.Image:
    raw = base64.b64decode(_strip_data_url(value.strip()))
    return Image.open(io.BytesIO(raw)).convert("RGB")


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def bgr_to_pil(image_bgr: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def resize_bgr(image_bgr: np.ndarray, max_dim: int = DEFAULT_MAX_DIM) -> np.ndarray:
    height, width = image_bgr.shape[:2]
    longest = max(height, width)
    if longest <= max_dim:
        return image_bgr
    scale = max_dim / float(longest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return cv2.resize(image_bgr, new_size, interpolation=cv2.INTER_AREA)


def decode_payload_image(payload: dict[str, Any], *, max_dim: int = DEFAULT_MAX_DIM) -> np.ndarray:
    """Decode image from analyze payload; returns BGR ndarray."""

    image_b64 = payload.get("image_base64")
    if image_b64:
        pil_image = image_from_base64(image_b64)
        return resize_bgr(pil_to_bgr(pil_image), max_dim=max_dim)

    image_url = payload.get("image_url")
    if image_url:
        raise ValueError("image_url fetching is not supported; provide image_base64")

    raise ValueError("No image provided: set image_base64")


def grayscale(image_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def aspect_ratio(image_bgr: np.ndarray) -> float:
    height, width = image_bgr.shape[:2]
    if height == 0:
        return 1.0
    return width / float(height)
