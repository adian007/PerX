"""Warm-mode hybrid recommendation service."""

from __future__ import annotations

import math

from app.models.recommendation import Perk, ScoreBreakdown, ScoredRecommendation

CONTENT_WEIGHT = 0.4
CF_WEIGHT = 0.4
UCB_WEIGHT = 0.2


def content_score(perk: Perk, affinity_vector: dict[str, float]) -> float:
    """Return the content-based category affinity score for a perk."""

    return float(affinity_vector.get(perk.category, 0.05))


def cf_score(perk: Perk, cf_scores: dict[str, float] | None = None) -> float:
    """Return the collaborative filtering score for a perk."""

    if cf_scores is not None:
        return float(cf_scores.get(perk.id, 0.0))
    return float(perk.collaborative_score)


def ucb_bonus(perk_id: str, ucb_counts: dict[str, int]) -> float:
    """Return the UCB exploration bonus for a perk."""

    total_interactions = sum(ucb_counts.values()) or 1
    shown_count = ucb_counts.get(perk_id, 0)
    if shown_count == 0:
        return 1.0
    return min(1.0, math.sqrt(2 * math.log(total_interactions) / shown_count))


def combine_scores(
    content_component: float, cf_component: float, ucb_component: float
) -> float:
    """Combine warm-mode scores with ADR-002 weights."""

    return (
        CONTENT_WEIGHT * content_component
        + CF_WEIGHT * cf_component
        + UCB_WEIGHT * ucb_component
    )


def compute_warm_recommendations(
    affinity_vector: dict[str, float],
    available_perks: list[Perk],
    budget_remaining_cents: int,
    ucb_counts: dict[str, int],
    cf_scores: dict[str, float] | None = None,
    limit: int = 20,
    category: str | None = None,
) -> list[ScoredRecommendation]:
    """Compute warm-mode recommendations from independent score components.

    TODO: Prefer nightly precomputed scores from Redis (`recs:{employee_id}:scores`)
    via ``RedisRecommendationCache`` when populated by the batch job. This function
    is the on-demand fallback path when cache is cold or bypassed with ``refresh``.
    """

    scored: list[ScoredRecommendation] = []
    for perk in available_perks:
        if not perk.is_active:
            continue
        if category is not None and perk.category != category:
            continue

        content_component = content_score(perk, affinity_vector)
        cf_component = cf_score(perk, cf_scores)
        ucb_component = ucb_bonus(perk.id, ucb_counts)
        final_score = combine_scores(content_component, cf_component, ucb_component)

        is_affordable = perk.employee_price_cents <= budget_remaining_cents
        if not is_affordable:
            final_score *= 0.1

        final_score = round(final_score, 6)
        scored.append(
            ScoredRecommendation(
                perk=perk,
                recommendation_score=final_score,
                reason_code="HYBRID",
                reason_text="Bazuar te preferencat e tua dhe çfarë zgjedhin punonjës të ngjashëm.",
                is_affordable=is_affordable,
                score_breakdown=ScoreBreakdown(
                    content_score=round(content_component, 6),
                    cf_score=round(cf_component, 6),
                    ucb_bonus=round(ucb_component, 6),
                    final_score=final_score,
                ),
            )
        )

    scored.sort(key=lambda recommendation: recommendation.recommendation_score, reverse=True)
    return scored[:limit]

