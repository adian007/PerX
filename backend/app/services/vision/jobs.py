"""Vision job orchestration and persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.models.vision import VisionJob
from app.schemas.vision import VisionAnalyzeRequest, VisionAnalyzeResponse, VisionJobData
from app.services.vision.client import analyze_with_cv_service


def _to_schema(job: VisionJob) -> VisionJobData:
    return VisionJobData(
        id=str(job.id),
        task=job.task,  # type: ignore[arg-type]
        status=job.status,  # type: ignore[arg-type]
        result=job.result_payload,
        error=job.error_payload,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
    )


async def create_and_process_job(
    db: AsyncSession,
    *,
    user: User,
    request: VisionAnalyzeRequest,
) -> VisionAnalyzeResponse:
    # Processed synchronously in-request so the client gets a completed job immediately.
    # BackgroundTasks would require a separate DB session and status polling; defer until
    # cv-service latency warrants async job queues.
    settings = get_settings()
    payload: dict[str, Any] = {
        "image_url": request.image_url,
        "image_base64": request.image_base64,
        "metadata": request.metadata,
    }
    if request.image_base64 and len(request.image_base64) > settings.cv_max_image_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "VISION_PAYLOAD_TOO_LARGE",
                "message": "image_base64 exceeds CV_MAX_IMAGE_BYTES",
                "details": {"limit": settings.cv_max_image_bytes},
            },
        )
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.cv_result_ttl_seconds)
    job = VisionJob(
        user_id=user.id,
        task=request.task,
        status="processing",
        request_payload=payload,
        expires_at=expires_at,
    )
    db.add(job)
    await db.flush()

    result, source = await analyze_with_cv_service(request.task, payload)
    job.status = "completed"
    job.result_payload = result
    job.completed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(job)

    return VisionAnalyzeResponse(job=_to_schema(job), source=source)


async def get_job(db: AsyncSession, *, user: User, job_id: UUID) -> VisionJobData:
    row = await db.scalar(select(VisionJob).where(VisionJob.id == job_id, VisionJob.user_id == user.id))
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "VISION_JOB_NOT_FOUND", "message": "Vision job not found", "details": {}},
        )
    return _to_schema(row)

