"""Internal routes — protected when INTERNAL_API_KEY is configured."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.schemas.recommendations import ApiEnvelope
from app.utils.envelope import envelope
from app.utils.ollama import EXPLANATION_STORE, check_ollama_health

router = APIRouter(tags=["internal"])


class LLMCallbackRequest(BaseModel):
    """Payload for async LLM callback storage."""

    model_config = ConfigDict(extra="forbid")

    employee_id: str
    type: str
    content: str
    job_id: str


async def verify_internal_access(
    x_internal_key: Annotated[str | None, Header(alias="X-Internal-Key")] = None,
) -> None:
    """Require internal API key when demo mode is off; open in dev when unset."""

    settings = get_settings()
    if settings.internal_api_key is None:
        if not settings.allow_demo_mode:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INTERNAL_API_DISABLED",
                    "message": "Internal API is not configured",
                    "details": {},
                },
            )
        return
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Invalid internal API key",
                "details": {},
            },
        )


@router.post("/internal/llm-callback", response_model=ApiEnvelope)
async def store_llm_callback(
    body: LLMCallbackRequest,
    _: Annotated[None, Depends(verify_internal_access)],
) -> dict[str, Any]:
    """Store an async LLM callback result."""

    EXPLANATION_STORE[body.employee_id] = body.content
    return envelope({"stored": True})


@router.get("/internal/ollama-health", response_model=ApiEnvelope)
async def ollama_health(
    _: Annotated[None, Depends(verify_internal_access)],
) -> dict[str, Any]:
    """Check whether Ollama is reachable and the configured model is available."""

    health = await check_ollama_health(get_settings())
    return envelope(health)
