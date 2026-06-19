"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.recommendations import ApiEnvelope
from app.utils.envelope import envelope

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiEnvelope)
async def health_check() -> dict:
    """Liveness probe for load balancers and Docker Compose."""

    return envelope({"status": "ok", "service": "perx-api"})
