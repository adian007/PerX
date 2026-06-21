"""Vision routes backed by optional cv-service."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.config import get_settings
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.recommendations import ApiEnvelope
from app.schemas.vision import VisionAnalyzeRequest
from app.services.vision.jobs import create_and_process_job, get_job
from app.utils.envelope import envelope

router = APIRouter(prefix="/vision", tags=["vision"])


@router.get("/health", response_model=ApiEnvelope)
async def vision_health(
    _: Annotated[
        User, Depends(require_role(UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin))
    ],
    __: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    settings = get_settings()
    return envelope(
        {
            "enabled": settings.cv_enabled,
            "service_url": settings.cv_service_url,
            "tasks": ["lifestyle", "receipt", "ocr", "catalog_tag", "visual_search"],
        }
    )


@router.post("/jobs", response_model=ApiEnvelope)
async def submit_vision_job(
    body: VisionAnalyzeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin)),
    ],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    result = await create_and_process_job(db, user=current_user, request=body)
    return envelope(result.model_dump(mode="json"))


@router.get("/jobs/{job_id}", response_model=ApiEnvelope)
async def get_vision_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.employee, UserRole.employer, UserRole.provider, UserRole.admin)),
    ],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    job = await get_job(db, user=current_user, job_id=job_id)
    return envelope(job.model_dump(mode="json"))

