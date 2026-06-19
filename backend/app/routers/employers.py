"""Employer routes — org-scoped via service layer."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.approvals import (
    ApproveResponseData,
    BulkApproveRequest,
    BulkApproveResponseData,
    RejectRequest,
    RejectResponseData,
)
from app.schemas.employer_analytics import EmployerAnalyticsData
from app.schemas.employer_employees import EmployerEmployeeListData
from app.schemas.employer_insights import EmployerInsightsData
from app.schemas.employers import EmployerOrganizationData
from app.schemas.recommendations import ApiEnvelope
from app.services.employer_analytics import get_employer_analytics
from app.services.employer_employees import list_employer_employees
from app.services.approvals import (
    approve_selection,
    bulk_approve_selections,
    get_pending_approvals,
    reject_selection,
)
from app.services.employer_insights import get_employer_insights
from app.services.employers import get_employer_organization
from app.utils.envelope import envelope
from app.utils.redis import RedisClient, get_redis

router = APIRouter(prefix="/employer", tags=["employers"])


@router.get("/organization", response_model=ApiEnvelope)
async def employer_organization(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Get the authenticated employer's organization."""

    data = await get_employer_organization(db, current_user)
    return envelope(EmployerOrganizationData.model_validate(data.model_dump()).model_dump())

@router.get("/employees", response_model=ApiEnvelope)
async def employer_employees(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    department: str | None = Query(None),
    search: str | None = Query(None),
) -> dict:
    """List employees with current-period budget summaries (org-scoped)."""

    data = await list_employer_employees(
        db,
        current_user,
        page=page,
        per_page=per_page,
        department=department,
        search=search,
    )
    payload = EmployerEmployeeListData.model_validate(data.model_dump()).model_dump()
    response = envelope(payload["employees"])
    response["meta"].update(
        {
            "total": payload["total"],
            "page": payload["page"],
            "per_page": payload["per_page"],
        }
    )
    return response


@router.get("/analytics", response_model=ApiEnvelope)
async def employer_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
    period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
) -> dict:
    """Org-scoped analytics from payments and selections."""

    data = await get_employer_analytics(db, current_user, period=period)
    return envelope(EmployerAnalyticsData.model_validate(data.model_dump()).model_dump())


@router.get("/insights", response_model=ApiEnvelope)
async def employer_insights(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Org-wide budget utilization and category insights for the current period."""

    data = await get_employer_insights(db, current_user)
    return envelope(EmployerInsightsData.model_validate(data.model_dump()).model_dump())


@router.get("/approvals", response_model=ApiEnvelope)
async def employer_approvals(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """Pending approval queue for the employer's organization."""

    items = await get_pending_approvals(db, current_user, page=page, per_page=per_page)
    payload = [item.model_dump() for item in items]
    response = envelope(payload)
    response["meta"].update(
        {"total": len(payload), "page": page, "per_page": per_page, "pages": 1}
    )
    return response


@router.post("/approvals/{selection_id}/approve", response_model=ApiEnvelope)
async def approve_pending_selection(
    selection_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Approve a pending selection (and package batch when applicable)."""

    data = await approve_selection(
        db,
        redis,
        current_user,
        selection_id,
        background_tasks,
    )
    return envelope(ApproveResponseData.model_validate(data.model_dump()).model_dump())


@router.post("/approvals/{selection_id}/reject", response_model=ApiEnvelope)
async def reject_pending_selection(
    selection_id: uuid.UUID,
    body: RejectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Reject a pending selection with a reason."""

    data = await reject_selection(
        db,
        redis,
        current_user,
        selection_id,
        reason=body.reason,
    )
    return envelope(RejectResponseData.model_validate(data.model_dump()).model_dump())


@router.post("/approvals/bulk-approve", response_model=ApiEnvelope)
async def bulk_approve_pending_selections(
    body: BulkApproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Approve multiple pending selections."""

    data = await bulk_approve_selections(
        db,
        redis,
        current_user,
        body.selection_ids,
        background_tasks,
    )
    return envelope(BulkApproveResponseData.model_validate(data.model_dump()).model_dump())
