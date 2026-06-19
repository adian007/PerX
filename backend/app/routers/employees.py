"""Employee routes — JWT + require_role(employee) per Auth and JWT Flow."""

from __future__ import annotations

from typing import Annotated

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.employees import BudgetSummaryData, EmployeeMeData
from app.schemas.recommendations import ApiEnvelope
from app.schemas.wishlist import WishlistAddResponseData
from app.services.employees import get_employee_budget, get_employee_me
from app.services.wishlist import add_to_wishlist, get_my_wishlist, remove_from_wishlist
from app.utils.envelope import envelope

router = APIRouter(tags=["employees"])


@router.get("/me", response_model=ApiEnvelope)
async def employee_me(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Get current employee profile."""

    data = await get_employee_me(db, current_user)
    return envelope(EmployeeMeData.model_validate(data.model_dump()).model_dump())


@router.get("/me/budget", response_model=ApiEnvelope)
async def employee_budget(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Get current month budget state."""

    data = await get_employee_budget(db, current_user)
    return envelope(BudgetSummaryData.model_validate(data.model_dump()).model_dump())


@router.get("/me/wishlist", response_model=ApiEnvelope)
async def my_wishlist(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Get the authenticated employee's wishlist."""

    items = await get_my_wishlist(db, current_user)
    response = envelope(items)
    response["meta"].update(
        {"total": len(items), "page": 1, "per_page": len(items) or 1, "pages": 1}
    )
    return response


@router.post(
    "/me/wishlist/{perk_id}",
    response_model=ApiEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def add_wishlist_item(
    perk_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Add a perk to the employee wishlist."""

    data = await add_to_wishlist(db, current_user, perk_id=perk_id)
    return envelope(WishlistAddResponseData.model_validate(data.model_dump()).model_dump())


@router.delete("/me/wishlist/{perk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wishlist_item(
    perk_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> Response:
    """Remove a perk from the employee wishlist."""

    await remove_from_wishlist(db, current_user, perk_id=perk_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
