"""Map database rows to recommendation dataclasses.

Column names align with ``database/migrations/001_initial.sql`` tables
``employee_profiles``, ``perks``, and ``provider_profiles``.
"""

from __future__ import annotations

from app.models.recommendation import EmployeeProfile, Perk, Provider, RecommenderMode


def employee_profile_from_row(row: dict) -> EmployeeProfile:
    """Build an ``EmployeeProfile`` from a Postgres row dict."""

    mode = row.get("recommender_mode", "cold_start")
    if mode not in ("cold_start", "warm"):
        mode = "cold_start"

    return EmployeeProfile(
        id=str(row["id"]),
        first_name=row["first_name"],
        interaction_count=int(row.get("interaction_count", 0)),
        recommender_mode=mode,  # type: ignore[arg-type]
        lifestyle_tags=list(row.get("lifestyle_tags") or []),
        preferred_categories=[
            str(category) for category in (row.get("preferred_categories") or [])
        ],
        budget_sensitivity=str(row.get("budget_sensitivity") or "medium"),
        wellness_priority=int(row.get("wellness_priority") or 5),
        family_situation=str(row.get("family_situation") or "single"),
        affinity_vector=row.get("affinity_vector"),
    )


def perk_from_row(row: dict, provider_row: dict) -> Perk:
    """Build a ``Perk`` from perk and provider Postgres row dicts."""

    provider = Provider(
        id=str(provider_row["id"]),
        company_name=provider_row["company_name"],
        logo_url=provider_row.get("logo_url"),
        avg_rating=float(provider_row.get("avg_rating") or 0.0),
    )
    return Perk(
        id=str(row["id"]),
        name=row["name"],
        category=str(row["category"]),
        short_description=row.get("short_description") or "",
        image_url=row.get("image_url"),
        employee_price_cents=int(row["employee_price_cents"]),
        provider=provider,
        tags=list(row.get("tags") or []),
        is_active=bool(row.get("is_active", True)),
        is_featured=bool(row.get("is_featured", False)),
        popularity_score=float(row.get("popularity_score") or 0.5),
        quality_score=float(row.get("quality_score") or 0.5),
        collaborative_score=float(row.get("collaborative_score") or 0.0),
    )


def ucb_counts_from_interactions(interactions: list[dict]) -> dict[str, int]:
    """Derive UCB show counts from ``perk_interactions`` rows.

    Counts each interaction where ``recommendation_rank`` is set, indicating
    the perk was shown as a recommendation.
    """

    counts: dict[str, int] = {}
    for interaction in interactions:
        if interaction.get("recommendation_rank") is None:
            continue
        perk_id = str(interaction["perk_id"])
        counts[perk_id] = counts.get(perk_id, 0) + 1
    return counts
