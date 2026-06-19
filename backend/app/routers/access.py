"""RBAC-protected stub routes for role boundary testing."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_role
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.recommendations import ApiEnvelope
from app.utils.envelope import envelope

router = APIRouter(tags=["access-control"])


@router.get("/me", response_model=ApiEnvelope)
async def employee_me(
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Employee-only profile stub."""

    return envelope({"role": current_user.role.value, "email": current_user.email})


@router.get("/employer/organization", response_model=ApiEnvelope)
async def employer_organization(
    current_user: Annotated[User, Depends(require_role(UserRole.employer))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Employer-only organization stub."""

    return envelope({"role": current_user.role.value, "email": current_user.email})


@router.get("/provider/profile", response_model=ApiEnvelope)
async def provider_profile(
    current_user: Annotated[User, Depends(require_role(UserRole.provider))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Provider-only profile stub."""

    return envelope({"role": current_user.role.value, "email": current_user.email})


@router.get("/admin/stats", response_model=ApiEnvelope)
async def admin_stats(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Admin-only stats stub."""

    return envelope({"role": current_user.role.value, "email": current_user.email})
