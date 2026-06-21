"""Color and scene heuristics from images."""

from __future__ import annotations

import cv2
import numpy as np

LIFESTYLE_LABELS = ("active", "family", "minimalist", "traveler", "wellness")
CATALOG_TAGS = ("fitness", "travel", "wellness", "food", "education", "entertainment")


def _channel_means(image_bgr: np.ndarray) -> tuple[float, float, float]:
    means = image_bgr.reshape(-1, 3).mean(axis=0)
    return float(means[2]), float(means[1]), float(means[0])  # R, G, B


def color_stats(image_bgr: np.ndarray) -> dict[str, float]:
    """Summarize hue, saturation, brightness, and channel balance."""

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].astype(np.float32)
    sat = hsv[:, :, 1].astype(np.float32) / 255.0
    val = hsv[:, :, 2].astype(np.float32) / 255.0

    r_mean, g_mean, b_mean = _channel_means(image_bgr)
    total = max(r_mean + g_mean + b_mean, 1.0)

    return {
        "brightness": float(val.mean()),
        "saturation": float(sat.mean()),
        "warmth": float((r_mean - b_mean) / 255.0),
        "red_ratio": r_mean / total,
        "green_ratio": g_mean / total,
        "blue_ratio": b_mean / total,
        "hue_std": float(hue.std()),
    }


def dominant_colors(image_bgr: np.ndarray, k: int = 3) -> list[tuple[int, int, int]]:
    """Return dominant RGB tuples via k-means on downsampled pixels."""

    small = cv2.resize(image_bgr, (64, 64), interpolation=cv2.INTER_AREA)
    pixels = small.reshape(-1, 3).astype(np.float32)
    if len(pixels) < k:
        return [(int(c[2]), int(c[1]), int(c[0])) for c in pixels[:k]]

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=k)
    order = np.argsort(counts)[::-1]
    colors: list[tuple[int, int, int]] = []
    for idx in order:
        b, g, r = centers[idx]
        colors.append((int(r), int(g), int(b)))
    return colors


def color_histogram(image_bgr: np.ndarray, bins_per_channel: int = 8) -> np.ndarray:
    """Normalized RGB histogram flattened to a vector."""

    hist_parts: list[np.ndarray] = []
    for channel in range(3):
        hist = cv2.calcHist([image_bgr], [channel], None, [bins_per_channel], [0, 256])
        hist = hist.flatten().astype(np.float32)
        total = hist.sum()
        if total > 0:
            hist /= total
        hist_parts.append(hist)
    return np.concatenate(hist_parts)


def lifestyle_scores(image_bgr: np.ndarray) -> dict[str, float]:
    """Heuristic lifestyle label scores mapped to PerX segments."""

    stats = color_stats(image_bgr)
    brightness = stats["brightness"]
    saturation = stats["saturation"]
    warmth = stats["warmth"]
    green = stats["green_ratio"]
    blue = stats["blue_ratio"]
    hue_var = stats["hue_std"]

    scores = {
        "active": 0.2 + green * 0.5 + saturation * 0.3 + (0.1 if brightness > 0.45 else 0.0),
        "family": 0.2 + max(warmth, 0.0) * 0.4 + saturation * 0.2 + (0.15 if warmth > 0.05 else 0.0),
        "minimalist": 0.25 + (1.0 - saturation) * 0.45 + brightness * 0.2,
        "traveler": 0.2 + blue * 0.45 + hue_var / 180.0 * 0.25,
        "wellness": 0.2 + green * 0.35 + (1.0 - abs(saturation - 0.35)) * 0.25,
    }
    return scores


def rank_lifestyle_labels(image_bgr: np.ndarray) -> list[tuple[str, float]]:
    scores = lifestyle_scores(image_bgr)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return ranked


def catalog_scores_from_colors(image_bgr: np.ndarray) -> dict[str, float]:
    stats = color_stats(image_bgr)
    r, g, b = stats["red_ratio"], stats["green_ratio"], stats["blue_ratio"]
    saturation = stats["saturation"]

    return {
        "fitness": 0.15 + g * 0.35 + saturation * 0.2,
        "travel": 0.15 + b * 0.4 + stats["hue_std"] / 200.0,
        "wellness": 0.15 + g * 0.3 + (1.0 - abs(saturation - 0.4)) * 0.2,
        "food": 0.15 + r * 0.45 + max(stats["warmth"], 0.0) * 0.2,
        "education": 0.15 + b * 0.2 + (1.0 - saturation) * 0.25,
        "entertainment": 0.15 + r * 0.25 + b * 0.25 + saturation * 0.2,
    }


def catalog_scores_from_keywords(text: str) -> dict[str, float]:
    lowered = text.lower()
    keyword_map = {
        "fitness": ("gym", "fitness", "sport", "run", "workout", "yoga"),
        "travel": ("travel", "flight", "hotel", "airport", "trip", "vacation"),
        "wellness": ("wellness", "spa", "health", "meditation", "mindful"),
        "food": ("food", "restaurant", "cafe", "coffee", "menu", "dining"),
        "education": ("book", "course", "learn", "school", "university", "class"),
        "entertainment": ("movie", "game", "music", "concert", "cinema", "show"),
    }
    scores = {tag: 0.0 for tag in CATALOG_TAGS}
    for tag, words in keyword_map.items():
        hits = sum(1 for word in words if word in lowered)
        if hits:
            scores[tag] = min(1.0, 0.35 + hits * 0.2)
    return scores
