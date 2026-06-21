"""Employee gamification routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.gamification import (
    GamificationPatchRequest,
    GamificationSnapshotData,
    QuizScoreRequest,
    ReviewCreateRequest,
)
from app.schemas.recommendations import ApiEnvelope
from app.services.gamification import (
    complete_journey_node,
    get_gamification_snapshot,
    patch_gamification,
    save_quiz_score,
    submit_review,
    unlock_achievement,
)
from app.utils.envelope import envelope

router = APIRouter(tags=["gamification"])


@router.get("/me/gamification", response_model=ApiEnvelope)
async def my_gamification(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Get full gamification snapshot for the authenticated employee."""

    data = await get_gamification_snapshot(db, current_user)
    return envelope(GamificationSnapshotData.model_validate(data.model_dump()).model_dump())


@router.patch("/me/gamification", response_model=ApiEnvelope)
async def update_my_gamification(
    body: GamificationPatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Update gamification fields such as marathoner miles or daily streak."""

    data = await patch_gamification(db, current_user, body)
    return envelope(GamificationSnapshotData.model_validate(data.model_dump()).model_dump())


@router.post("/me/journey/{category}/complete", response_model=ApiEnvelope)
async def complete_journey_category(
    category: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Mark a journey path node complete."""

    data = await complete_journey_node(db, current_user, category=category)
    return envelope(GamificationSnapshotData.model_validate(data.model_dump()).model_dump())


@router.put("/me/quiz/{category}", response_model=ApiEnvelope)
async def upsert_quiz_score(
    category: str,
    body: QuizScoreRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Save best quiz score for a category."""

    data = await save_quiz_score(db, current_user, category=category, body=body)
    return envelope(GamificationSnapshotData.model_validate(data.model_dump()).model_dump())


@router.post(
    "/me/achievements/{slug}/unlock",
    response_model=ApiEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def unlock_my_achievement(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Unlock an achievement by slug."""

    data = await unlock_achievement(db, current_user, slug=slug)
    return envelope(GamificationSnapshotData.model_validate(data.model_dump()).model_dump())


@router.post(
    "/me/reviews",
    response_model=ApiEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_review(
    body: ReviewCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Submit or update a perk review."""

    data = await submit_review(db, current_user, body)
    return envelope(GamificationSnapshotData.model_validate(data.model_dump()).model_dump())
