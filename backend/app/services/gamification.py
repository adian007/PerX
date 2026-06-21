"""Employee gamification business logic."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import (
    Achievement,
    EmployeeAchievement,
    EmployeeGamification,
    EmployeeReview,
    JourneyProgress,
    QuizScore,
)
from app.models.user import User
from app.repositories.wishlist import list_wishlist_items
from app.schemas.gamification import (
    GamificationPatchRequest,
    GamificationSnapshotData,
    PerkReviewData,
    QuizScoreRequest,
    ReviewCreateRequest,
)
from app.services.access_control import require_employee_profile

LEVEL_THRESHOLDS: list[tuple[int, str, int]] = [
    (1, "I ri", 0),
    (2, "Eksplorues", 150),
    (3, "Ekspert përfitimesh", 400),
    (4, "Strateg", 800),
    (5, "Pro përfitimesh", 1500),
]

POINTS = {
    "CLAIM_PERK": 75,
    "QUIZ_BONUS": 50,
    "PATH_NODE": 40,
    "REVIEW": 25,
    "QUIZ_PERFECT": 30,
    "DAILY_STREAK": 10,
    "WISHLIST": 15,
}

XP = {
    "CLAIM_PERK": 30,
    "QUIZ_BONUS": 10,
    "PATH_NODE": 20,
    "REVIEW": 10,
    "QUIZ_PERFECT": 25,
    "WISHLIST": 5,
}

JOURNEY_CATEGORIES = ("food", "fitness", "wellness", "travel")


def compute_level(xp: int) -> tuple[int, str, int]:
    """Return level, class label, and XP threshold for next level."""

    level = 1
    class_label = LEVEL_THRESHOLDS[0][1]
    for lvl, label, threshold in LEVEL_THRESHOLDS:
        if xp >= threshold:
            level = lvl
            class_label = label
    next_threshold = next((t for lvl, _, t in LEVEL_THRESHOLDS if lvl == level + 1), LEVEL_THRESHOLDS[-1][2])
    return level, class_label, next_threshold


async def get_or_create_gamification(db: AsyncSession, user_id: uuid.UUID) -> EmployeeGamification:
    """Load or initialize gamification row for a user."""

    row = await db.scalar(
        select(EmployeeGamification).where(EmployeeGamification.user_id == user_id)
    )
    if row is not None:
        return row

    row = EmployeeGamification(user_id=user_id)
    db.add(row)
    await db.flush()
    return row


def _apply_xp_and_points(
    gamification: EmployeeGamification,
    *,
    points: int = 0,
    xp: int = 0,
) -> None:
    if points:
        gamification.points += points
    if xp:
        gamification.xp += xp
        level, class_label, _ = compute_level(gamification.xp)
        gamification.level = level
        gamification.class_label = class_label
    gamification.updated_at = datetime.now(timezone.utc)


async def _build_snapshot(db: AsyncSession, user: User) -> GamificationSnapshotData:
    gamification = await get_or_create_gamification(db, user.id)
    _, class_label, xp_to_next = compute_level(gamification.xp)

    journey_rows = await db.scalars(
        select(JourneyProgress.category).where(JourneyProgress.user_id == user.id)
    )
    quiz_rows = await db.scalars(select(QuizScore).where(QuizScore.user_id == user.id))
    achievement_rows = await db.scalars(
        select(EmployeeAchievement).where(EmployeeAchievement.user_id == user.id)
    )
    review_rows = await db.scalars(select(EmployeeReview).where(EmployeeReview.user_id == user.id))

    achievement_list = achievement_rows.all()
    unlocked_at_by_slug = {
        row.achievement_slug: row.unlocked_at.isoformat() for row in achievement_list
    }

    quiz_progress = {row.category: row.score for row in quiz_rows.all()}
    reviews = [
        PerkReviewData(
            perk_id=str(review.perk_id),
            rating=review.rating,
            feedback=review.feedback,
            submitted_at=review.created_at.isoformat(),
        )
        for review in review_rows.all()
    ]

    last_active = (
        gamification.last_active_date.isoformat() if gamification.last_active_date else None
    )

    return GamificationSnapshotData(
        level=gamification.level,
        class_label=class_label,
        xp=gamification.xp,
        xp_to_next_level=xp_to_next,
        streak_days=gamification.streak_days,
        points_balance=gamification.points,
        last_active_date=last_active,
        completed_path_nodes=list(journey_rows.all()),
        unlocked_achievements=list(unlocked_at_by_slug.keys()),
        unlocked_at_by_slug=unlocked_at_by_slug,
        quiz_progress=quiz_progress,
        reviews=reviews,
        marathoner_miles=gamification.marathoner_miles,
    )


async def get_gamification_snapshot(db: AsyncSession, user: User) -> GamificationSnapshotData:
    """Return full gamification state for the authenticated employee."""

    await require_employee_profile(db, user)
    return await _build_snapshot(db, user)


async def patch_gamification(
    db: AsyncSession,
    user: User,
    body: GamificationPatchRequest,
) -> GamificationSnapshotData:
    """Update optional gamification fields."""

    gamification = await get_or_create_gamification(db, user.id)

    if body.marathoner_miles is not None:
        gamification.marathoner_miles = body.marathoner_miles
        if body.marathoner_miles >= 100:
            await unlock_achievement(db, user, slug="marathoner", award_points=False)

    if body.record_daily_visit:
        await _record_daily_visit(db, gamification)

    await db.flush()
    return await _build_snapshot(db, user)


async def _record_daily_visit(db: AsyncSession, gamification: EmployeeGamification) -> None:
    today = datetime.now(timezone.utc).date()
    if gamification.last_active_date == today:
        return

    yesterday = today - timedelta(days=1)
    if gamification.last_active_date == yesterday:
        gamification.streak_days += 1
    else:
        gamification.streak_days = 1

    gamification.last_active_date = today
    _apply_xp_and_points(gamification, points=POINTS["DAILY_STREAK"])


async def complete_journey_node(
    db: AsyncSession,
    user: User,
    *,
    category: str,
    award_points: bool = True,
) -> GamificationSnapshotData:
    """Mark a journey category complete and award points once."""

    await require_employee_profile(db, user)
    existing = await db.scalar(
        select(JourneyProgress).where(
            JourneyProgress.user_id == user.id,
            JourneyProgress.category == category,
        )
    )
    if existing is not None:
        return await _build_snapshot(db, user)

    gamification = await get_or_create_gamification(db, user.id)
    db.add(
        JourneyProgress(
            user_id=user.id,
            category=category,
            status="completed",
        )
    )
    if award_points:
        _apply_xp_and_points(
            gamification,
            points=POINTS["PATH_NODE"],
            xp=XP["PATH_NODE"],
        )
        await unlock_achievement(db, user, slug="first-steps", award_points=False)

    completed = await db.scalars(
        select(JourneyProgress.category).where(JourneyProgress.user_id == user.id)
    )
    if set(completed.all()) >= set(JOURNEY_CATEGORIES):
        await unlock_achievement(db, user, slug="well-rounded", award_points=False)

    await db.flush()
    return await _build_snapshot(db, user)


async def save_quiz_score(
    db: AsyncSession,
    user: User,
    *,
    category: str,
    body: QuizScoreRequest,
) -> GamificationSnapshotData:
    """Persist best quiz score and award path/quiz bonuses."""

    await require_employee_profile(db, user)
    if body.score > body.total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_QUIZ_SCORE",
                "message": "Score cannot exceed total",
                "details": {},
            },
        )

    existing = await db.scalar(
        select(QuizScore).where(
            QuizScore.user_id == user.id,
            QuizScore.category == category,
        )
    )
    prev_score = existing.score if existing else 0
    new_score = max(prev_score, body.score)

    if existing is None:
        db.add(
            QuizScore(
                user_id=user.id,
                category=category,
                score=new_score,
                total=body.total,
            )
        )
    elif new_score > existing.score:
        existing.score = new_score
        existing.total = body.total
        existing.updated_at = datetime.now(timezone.utc)

    gamification = await get_or_create_gamification(db, user.id)
    passing_threshold = (body.total * 60 + 99) // 100  # ceil(60%)
    if body.score >= passing_threshold and category != "default":
        await complete_journey_node(db, user, category=category, award_points=True)

    if body.score == body.total and body.score > prev_score:
        _apply_xp_and_points(
            gamification,
            points=POINTS["QUIZ_PERFECT"],
            xp=XP["QUIZ_PERFECT"],
        )

    await db.flush()
    return await _build_snapshot(db, user)


async def unlock_achievement(
    db: AsyncSession,
    user: User,
    *,
    slug: str,
    award_points: bool = False,
) -> GamificationSnapshotData:
    """Unlock an achievement if it exists in the catalog."""

    await require_employee_profile(db, user)

    achievement = await db.scalar(select(Achievement).where(Achievement.slug == slug))
    if achievement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ACHIEVEMENT_NOT_FOUND",
                "message": "Achievement not found",
                "details": {},
            },
        )

    existing = await db.scalar(
        select(EmployeeAchievement).where(
            EmployeeAchievement.user_id == user.id,
            EmployeeAchievement.achievement_slug == slug,
        )
    )
    if existing is None:
        db.add(
            EmployeeAchievement(
                user_id=user.id,
                achievement_slug=slug,
            )
        )
        if award_points:
            gamification = await get_or_create_gamification(db, user.id)
            _apply_xp_and_points(gamification, xp=10)

    await db.flush()
    return await _build_snapshot(db, user)


async def submit_review(
    db: AsyncSession,
    user: User,
    body: ReviewCreateRequest,
) -> GamificationSnapshotData:
    """Persist a perk review and award first-review points."""

    await require_employee_profile(db, user)

    try:
        perk_uuid = uuid.UUID(body.perk_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PERK_ID",
                "message": "Invalid perk id",
                "details": {},
            },
        ) from exc

    existing = await db.scalar(
        select(EmployeeReview).where(
            EmployeeReview.user_id == user.id,
            EmployeeReview.perk_id == perk_uuid,
        )
    )
    is_new = existing is None
    if existing is None:
        db.add(
            EmployeeReview(
                user_id=user.id,
                perk_id=perk_uuid,
                rating=body.rating,
                feedback=body.feedback,
            )
        )
    else:
        existing.rating = body.rating
        existing.feedback = body.feedback

    if is_new:
        gamification = await get_or_create_gamification(db, user.id)
        _apply_xp_and_points(
            gamification,
            points=POINTS["REVIEW"],
            xp=XP["REVIEW"],
        )

    await db.flush()
    return await _build_snapshot(db, user)


async def award_wishlist_add(db: AsyncSession, user: User) -> None:
    """Award points for adding to wishlist and check curator achievement."""

    gamification = await get_or_create_gamification(db, user.id)
    _apply_xp_and_points(
        gamification,
        points=POINTS["WISHLIST"],
        xp=XP["WISHLIST"],
    )

    profile = await require_employee_profile(db, user)
    items = await list_wishlist_items(db, profile.id)
    if len(items) >= 5:
        await unlock_achievement(db, user, slug="wishlist-curator", award_points=False)

    await db.flush()


async def award_quick_add(
    db: AsyncSession,
    user: User,
    *,
    category: str,
) -> None:
    """Award points for quick-add selection and related achievements."""

    gamification = await get_or_create_gamification(db, user.id)
    _apply_xp_and_points(
        gamification,
        points=POINTS["CLAIM_PERK"],
        xp=XP["CLAIM_PERK"],
    )
    await complete_journey_node(db, user, category=category, award_points=False)
    await unlock_achievement(db, user, slug="smart-spender", award_points=False)
    await db.flush()
