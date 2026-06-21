"""Gamification API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PerkReviewData(BaseModel):
    """Employee perk review."""

    model_config = ConfigDict(strict=True)

    perk_id: str
    rating: int = Field(ge=1, le=5)
    feedback: str = ""
    submitted_at: str


class GamificationSnapshotData(BaseModel):
    """Full gamification state for GET /me/gamification."""

    model_config = ConfigDict(strict=True)

    level: int
    class_label: str
    xp: int
    xp_to_next_level: int
    streak_days: int
    points_balance: int
    last_active_date: str | None = None
    completed_path_nodes: list[str]
    unlocked_achievements: list[str]
    unlocked_at_by_slug: dict[str, str]
    quiz_progress: dict[str, int]
    reviews: list[PerkReviewData]
    marathoner_miles: int


class GamificationPatchRequest(BaseModel):
    """PATCH /me/gamification body."""

    model_config = ConfigDict(strict=True)

    marathoner_miles: int | None = Field(default=None, ge=0, le=1000)
    record_daily_visit: bool = False


class QuizScoreRequest(BaseModel):
    """PUT /me/quiz/{category} body."""

    model_config = ConfigDict(strict=True)

    score: int = Field(ge=0)
    total: int = Field(ge=1)


class ReviewCreateRequest(BaseModel):
    """POST /me/reviews body."""

    model_config = ConfigDict(strict=True)

    perk_id: str
    rating: int = Field(ge=1, le=5)
    feedback: str = ""
