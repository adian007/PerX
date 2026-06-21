"""Lightweight image embeddings for visual similarity."""

from __future__ import annotations

import hashlib
from typing import Any

import imagehash
import numpy as np

from app.utils.colors import color_histogram
from app.utils.image import aspect_ratio, bgr_to_pil


def _hash_bits(phash: imagehash.ImageHash) -> np.ndarray:
    bits = phash.hash.flatten().astype(np.float32)
    return bits


def compute_embedding(image_bgr: np.ndarray) -> np.ndarray:
    """Concatenate color histogram, perceptual hashes, and simple scene scalars."""

    pil = bgr_to_pil(image_bgr)
    hist = color_histogram(image_bgr, bins_per_channel=8)
    phash = _hash_bits(imagehash.phash(pil))
    dhash = _hash_bits(imagehash.dhash(pil))
    ahash = _hash_bits(imagehash.average_hash(pil))

    hsv_mean = image_bgr.mean(axis=(0, 1)) / 255.0
    scalars = np.array(
        [aspect_ratio(image_bgr), float(hsv_mean[0]), float(hsv_mean[1]), float(hsv_mean[2])],
        dtype=np.float32,
    )

    vector = np.concatenate([hist, phash, dhash, ahash, scalars]).astype(np.float32)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector /= norm
    return vector


def embedding_hash(embedding: np.ndarray) -> str:
    digest = hashlib.sha256(embedding.tobytes()).hexdigest()
    return f"emb-{digest[:16]}"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def pseudo_matches_from_embedding(embedding: np.ndarray, top_k: int = 3) -> list[dict[str, Any]]:
    """Derive stable placeholder perk IDs from embedding segments (no index required)."""

    matches: list[dict[str, Any]] = []
    for i in range(top_k):
        segment = embedding[i * 8 : (i + 1) * 8]
        seed = int(hashlib.md5(segment.tobytes()).hexdigest()[:8], 16)
        score = round(0.75 + (seed % 20) / 100.0, 2)
        matches.append({"item_id": f"perk-{100 + (seed % 900)}", "score": score})
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches


def visual_search_result(image_bgr: np.ndarray) -> dict[str, Any]:
    embedding = compute_embedding(image_bgr)
    return {
        "embedding": embedding.tolist(),
        "embedding_dim": int(embedding.shape[0]),
        "query_embedding_hash": embedding_hash(embedding),
        "matches": pseudo_matches_from_embedding(embedding),
    }
