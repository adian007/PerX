"""Mode-switching service for the PerX recommender."""

from __future__ import annotations

from app.config import get_settings
from app.models.recommendation import EmployeeProfile, RecommenderMode


def determine_recommender_mode(
    interaction_count: int,
    current_mode: RecommenderMode = "cold_start",
    warm_threshold: int | None = None,
) -> RecommenderMode:
    """Return the recommender mode for an employee.

    The transition is one-way. A profile already marked warm remains warm even
    if the count passed to this function is later lower than the threshold.
    """

    threshold = warm_threshold
    if threshold is None:
        threshold = get_settings().recommender_warm_threshold

    if current_mode == "warm":
        return "warm"
    if interaction_count >= threshold:
        return "warm"
    return "cold_start"


def mode_for_employee(
    employee: EmployeeProfile, warm_threshold: int | None = None
) -> RecommenderMode:
    """Return the recommender mode for an employee profile."""

    return determine_recommender_mode(
        interaction_count=employee.interaction_count,
        current_mode=employee.recommender_mode,
        warm_threshold=warm_threshold,
    )

