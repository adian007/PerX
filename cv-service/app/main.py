"""Standalone optional CV microservice."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import settings
from app.registry import PIPELINE_REGISTRY
from app.schemas.vision import AnalyzeRequest, AnalyzeResponse

app = FastAPI(title="PerX CV Service", version=settings.service_version)


async def verify_cv_internal_key(
    x_cv_internal_key: Annotated[str | None, Header(alias="X-CV-Internal-Key")] = None,
) -> None:
    """Require shared secret when CV_INTERNAL_KEY is configured."""

    if settings.internal_key is None:
        return
    if x_cv_internal_key != settings.internal_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-CV-Internal-Key",
        )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.service_version,
        "tasks": sorted(PIPELINE_REGISTRY.keys()),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    _: Annotated[None, Depends(verify_cv_internal_key)],
) -> AnalyzeResponse:
    pipeline = PIPELINE_REGISTRY.get(request.task)
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported task: {request.task}",
        )

    payload = request.model_dump()
    if payload.get("image_base64") and len(payload["image_base64"]) > settings.max_payload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="image_base64 exceeds CV_MAX_PAYLOAD_BYTES",
        )

    result = pipeline.run(payload)
    technique = result.get("technique", "built-in")
    return AnalyzeResponse(
        task=request.task,
        result=result,
        meta={"pipeline": pipeline.task_name, "technique": technique},
    )

