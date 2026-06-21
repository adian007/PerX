"""Async Ollama client and deterministic explanation fallbacks."""

from __future__ import annotations

import logging
import uuid
from typing import MutableMapping

import httpx

from sqlalchemy import select

from app.config import Settings, get_settings
from app.database import AsyncSessionLocal
from app.models.employee import EmployeeProfile
from app.services.websocket_gateway import get_websocket_gateway

logger = logging.getLogger(__name__)

EXPLANATION_STORE: MutableMapping[str, str] = {}


def get_fallback_explanation(top_category: str, employee_name: str) -> str:
    """Return a deterministic explanation keyed by top affinity category."""

    fallbacks = {
        "fitness": (
            f"Vendosëm përfitime fitness për ty, {employee_name}, "
            "sepse ke treguar interes për aktivitet fizik."
        ),
        "wellness": (
            f"Përfitimet e mirëqenies janë në krye për ty, {employee_name}, "
            "me opsione për relaksim dhe balancë."
        ),
        "food": (
            f"Theksuam përfitimet e ushqimit për ty, {employee_name}, "
            "nga subvencione ushqimi te partnerë dërgese."
        ),
        "travel": (
            f"Përfitimet e udhëtimit dalin në krye për ty, {employee_name}, "
            "që të udhëtosh më shumë me më pak kosto."
        ),
        "education": (
            f"Mundësitë e mësimit janë në fokus për ty, {employee_name}, "
            "me përfitime që ndihmojnë zhvillimin profesional."
        ),
        "transport": (
            f"Vendosëm përfitime transporti për ty, {employee_name}, "
            "për ta bërë komutimin dhe lëvizjen lokale më të lehtë."
        ),
        "childcare": (
            f"Përfitimet për familjen dalin në krye për ty, {employee_name}, "
            "me opsione kujdesi për fëmijët."
        ),
    }
    return fallbacks.get(
        top_category,
        f"Sipas profilit tënd, {employee_name}, prioritet kanë përfitimet e kategorisë {top_category}.",
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

Write a 2-3 sentence personalized explanation in Albanian (sq-AL) of why these benefit categories were chosen.
Use informal "ti" form. Be specific and concise. Do not use em dashes.
Do not use generic phrases like "based on your data".
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


async def generate_chat_reply(
    message: str,
    employee_name: str,
    context: str,
    history: list[tuple[str, str]] | None = None,
    settings: Settings | None = None,
) -> tuple[str, str, str]:
    """Generate a chat reply via Ollama. Returns (reply, model, source)."""

    active_settings = settings or get_settings()
    model = active_settings.ollama_model

    fallback = (
        f"Hi {employee_name}. I can help with your budget and benefits. "
        "Check recommendations on the home screen or ask about a specific category."
    )

    if active_settings.ollama_force_fail:
        return fallback, model, "fallback"

    history_block = ""
    if history:
        lines = []
        for role, content in history[-6:]:
            speaker = "Employee" if role == "user" else "PerX"
            lines.append(f"{speaker}: {content}")
        history_block = "Recent conversation:\n" + "\n".join(lines) + "\n\n"

    prompt = f"""You are PerX, a professional employee benefits assistant.
Use ONLY the context below and the recent conversation. If unsure, say so briefly and suggest checking the app.
Always reply in English. No markdown. No em dashes. Keep answers to 2-4 sentences.

Example:
CONTEXT:
Employee: Jane Doe
Employer: Acme Corp
Budget remaining: 12,500 ALL (ALL)
Top recommendations: Yoga Pass (45 ALL/mo)

Employee question: How much budget do I have left?

PerX reply: Hi Jane, you have 12,500 ALL remaining in your benefits budget this month. You can use it toward perks like Yoga Pass from the home screen.

{history_block}CONTEXT:
{context}

Employee question: {message}

PerX reply:"""

    try:
        async with httpx.AsyncClient(timeout=active_settings.ollama_timeout_seconds) as client:
            response = await client.post(
                f"{active_settings.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            content = response.json().get("response", "").strip()
            if content:
                return content, model, "ollama"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama chat failed: %s", exc)

    return fallback, model, "fallback"


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

    explanation = await generate_or_fallback_explanation(
        affinity_vector=affinity_vector,
        top_categories=top_categories,
        employee_name=employee_name,
        settings=settings,
    )
    EXPLANATION_STORE[employee_id] = explanation

    try:
        profile_uuid = uuid.UUID(employee_id)
    except ValueError:
        return

    try:
        async with AsyncSessionLocal() as db:
            profile = await db.scalar(
                select(EmployeeProfile).where(EmployeeProfile.id == profile_uuid)
            )
            if profile is None:
                return
            profile.welcome_explanation = explanation
            await db.commit()
    except Exception as exc:  # noqa: BLE001 - background task must not leak failures
        logger.warning(
            "Failed to persist welcome_explanation for employee %s: %s",
            employee_id,
            exc,
        )
        return

    gateway = get_websocket_gateway()
    await gateway.broadcast_to_employee(
        employee_id,
        "llm_ready",
        {"employee_id": employee_id, "explanation_preview": explanation[:120]},
    )

