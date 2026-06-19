"""Async Ollama client and deterministic explanation fallbacks."""

from __future__ import annotations

import logging
from typing import MutableMapping

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

EXPLANATION_STORE: MutableMapping[str, str] = {}


def get_fallback_explanation(top_category: str, employee_name: str) -> str:
    """Return a deterministic explanation keyed by top affinity category."""

    fallbacks = {
        "fitness": (
            f"We prioritized fitness benefits for you, {employee_name}, to support "
            "an active, energized lifestyle."
        ),
        "wellness": (
            f"Your benefits focus on wellness, {employee_name}, with options that "
            "help you recharge and stay balanced."
        ),
        "food": (
            f"We highlighted food benefits for you, {employee_name}, from healthy "
            "meal support to everyday dining perks."
        ),
        "travel": (
            f"Travel perks take center stage in your recommendations, {employee_name}, "
            "so you can explore more for less."
        ),
        "education": (
            f"Learning opportunities are front and center for you, {employee_name}, "
            "with benefits that help you grow your skills."
        ),
        "transport": (
            f"We prioritized transport benefits for you, {employee_name}, to make "
            "commuting and local travel easier."
        ),
        "childcare": (
            f"Family-friendly benefits are prominent for you, {employee_name}, with "
            "supportive childcare options near the top."
        ),
    }
    return fallbacks.get(
        top_category,
        f"Based on your profile, we prioritized {top_category} benefits for you.",
    )


async def generate_recommendation_explanation(
    affinity_vector: dict[str, float],
    top_categories: list[str],
    employee_name: str,
    settings: Settings | None = None,
) -> str | None:
    """Generate an explanation with Ollama.

    This function must only be called from FastAPI BackgroundTasks. It returns
    None on failure so deterministic callers can use the template fallback.
    """

    active_settings = settings or get_settings()
    if active_settings.ollama_force_fail:
        logger.info("OLLAMA_FORCE_FAIL enabled; using fallback explanation")
        return None

    prompt = f"""You are a friendly HR assistant for a benefits marketplace.
An employee named {employee_name} has these benefit preferences (scored 0-1):
{', '.join(f'{key}: {value:.2f}' for key, value in affinity_vector.items())}

Their top categories are: {', '.join(top_categories)}.

Write a 2-3 sentence personalized explanation of why these benefit categories were chosen for them.
Be warm, specific, and concise. Do not use generic phrases like "based on your data".
Focus on their lifestyle and what they will gain."""

    attempts = max(1, active_settings.ollama_max_retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(
                timeout=active_settings.ollama_timeout_seconds
            ) as client:
                response = await client.post(
                    f"{active_settings.ollama_base_url}/api/generate",
                    json={
                        "model": active_settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                content = response.json().get("response", "")
                explanation = content.strip()
                if explanation:
                    return explanation
                logger.warning(
                    "Ollama returned empty explanation on attempt %s/%s",
                    attempt,
                    attempts,
                )
        except Exception as exc:  # noqa: BLE001 - background task must not leak failures
            logger.warning(
                "Ollama explanation generation failed on attempt %s/%s: %s",
                attempt,
                attempts,
                exc,
            )
    return None


async def check_ollama_health(
    settings: Settings | None = None,
) -> dict[str, bool | str]:
    """Return Ollama reachability and model availability for diagnostics."""

    active_settings = settings or get_settings()
    if active_settings.ollama_force_fail:
        return {
            "reachable": False,
            "model_available": False,
            "model": active_settings.ollama_model,
            "base_url": active_settings.ollama_base_url,
            "reason": "OLLAMA_FORCE_FAIL enabled",
        }

    try:
        async with httpx.AsyncClient(
            timeout=active_settings.ollama_timeout_seconds
        ) as client:
            response = await client.get(f"{active_settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = {model.get("name", "") for model in models}
            configured = active_settings.ollama_model
            model_available = any(
                name == configured or name.startswith(f"{configured}:")
                for name in model_names
            )
            return {
                "reachable": True,
                "model_available": model_available,
                "model": configured,
                "base_url": active_settings.ollama_base_url,
            }
    except Exception as exc:  # noqa: BLE001 - health endpoint reports failure
        logger.warning("Ollama health check failed: %s", exc)
        return {
            "reachable": False,
            "model_available": False,
            "model": active_settings.ollama_model,
            "base_url": active_settings.ollama_base_url,
            "reason": str(exc),
        }


async def generate_or_fallback_explanation(
    affinity_vector: dict[str, float],
    top_categories: list[str],
    employee_name: str,
    settings: Settings | None = None,
) -> str:
    """Generate an explanation or return the deterministic fallback."""

    explanation = await generate_recommendation_explanation(
        affinity_vector=affinity_vector,
        top_categories=top_categories,
        employee_name=employee_name,
        settings=settings,
    )
    if explanation is not None:
        return explanation
    return get_fallback_explanation(top_categories[0], employee_name)


async def generate_and_store_explanation(
    employee_id: str,
    affinity_vector: dict[str, float],
    top_categories: list[str],
    employee_name: str,
    settings: Settings | None = None,
) -> None:
    """Background task that stores either the Ollama result or fallback text."""

    EXPLANATION_STORE[employee_id] = await generate_or_fallback_explanation(
        affinity_vector=affinity_vector,
        top_categories=top_categories,
        employee_name=employee_name,
        settings=settings,
    )

