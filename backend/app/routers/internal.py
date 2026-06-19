"""Internal routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.recommendations import ApiEnvelope
from app.utils.envelope import envelope
from app.utils.ollama import EXPLANATION_STORE, check_ollama_health

router = APIRouter(tags=["internal"])


class LLMCallbackRequest(BaseModel):
    """Payload for async LLM callback storage."""

    employee_id: str
    type: str
    content: str
    job_id: str


@router.post("/internal/llm-callback", response_model=ApiEnvelope)
async def store_llm_callback(body: LLMCallbackRequest) -> dict[str, Any]:
    """Store an async LLM callback result."""

    EXPLANATION_STORE[body.employee_id] = body.content
    return envelope({"stored": True})


@router.get("/internal/ollama-health", response_model=ApiEnvelope)
async def ollama_health() -> dict[str, Any]:
    """Check whether Ollama is reachable and the configured model is available."""

    health = await check_ollama_health(get_settings())
    return envelope(health)
