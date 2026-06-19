"""Curated package routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.packages import PackageListItem, PackageSelectionResponseData
from app.schemas.recommendations import ApiEnvelope
from app.services.packages import list_packages_for_employees, select_package
from app.utils.envelope import envelope
from app.utils.redis import RedisClient, get_redis

router = APIRouter(tags=["packages"])


@router.get("/packages", response_model=ApiEnvelope)
async def list_packages(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """List active curated packages for employees."""

    items = await list_packages_for_employees(db)
    payload = [PackageListItem.model_validate(item.model_dump()).model_dump() for item in items]
    return envelope(payload)


@router.post("/selections/package/{package_id}", response_model=ApiEnvelope)
async def select_package_route(
    package_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Create pending selections for all perks in a package."""

    data = await select_package(db, redis, current_user, package_id)
    return envelope(PackageSelectionResponseData.model_validate(data.model_dump()).model_dump())
