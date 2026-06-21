"""Cold-start recommendation service."""

from __future__ import annotations

from app.models.recommendation import CATEGORIES, Perk, ScoredRecommendation

CATEGORY_WEIGHTS = {
    "cyclist": {"transport": 0.4, "fitness": 0.2},
    "remote_worker": {"education": 0.2, "wellness": 0.2, "food": 0.15},
    "parent": {"childcare": 0.5, "education": 0.2, "entertainment": 0.15},
    "gym_goer": {"fitness": 0.5},
    "foodie": {"food": 0.5},
    "traveler": {"travel": 0.6},
    "reader": {"education": 0.3, "entertainment": 0.2},
    "yogi": {"wellness": 0.5, "fitness": 0.2},
}

CATEGORY_LABELS = {
    "fitness": "fitness",
    "wellness": "mirëqenie",
    "food": "ushqim",
    "travel": "udhëtim",
    "transport": "transport",
    "finance": "financë",
    "education": "arsim",
    "entertainment": "argëtim",
    "childcare": "kujdes fëmijësh",
}


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category.replace("_", " "))


WELLNESS_WEIGHT = 0.08


def compute_affinity_vector(
    lifestyle_tags: list[str],
    preferred_categories: list[str],
    budget_sensitivity: str,
    wellness_priority: int,
    family_situation: str,
) -> dict[str, float]:
    """Compute deterministic category affinity from onboarding answers."""

    del budget_sensitivity
    scores = {category: 0.0 for category in CATEGORIES}

    for tag in lifestyle_tags:
        for category, weight in CATEGORY_WEIGHTS.get(tag, {}).items():
            scores[category] = min(1.0, scores[category] + weight)

    for category in preferred_categories:
        if category in scores:
            scores[category] = min(1.0, scores[category] + 0.3)

    scores["wellness"] = min(1.0, scores["wellness"] + wellness_priority * WELLNESS_WEIGHT)

    if family_situation == "family":
        scores["childcare"] = min(1.0, scores["childcare"] + 0.3)
        scores["entertainment"] = min(1.0, scores["entertainment"] + 0.15)

    for category in scores:
        scores[category] = max(0.05, round(scores[category], 4))

    return scores


def top_affinity_categories(
    affinity_vector: dict[str, float], limit: int = 3
) -> list[str]:
    """Return the highest-affinity categories."""

    return [
        category
        for category, _score in sorted(
            affinity_vector.items(), key=lambda item: item[1], reverse=True
        )[:limit]
    ]


def score_cold_start_recommendations(
    affinity_vector: dict[str, float],
    available_perks: list[Perk],
    budget_remaining_cents: int,
    limit: int = 20,
    category: str | None = None,
) -> list[ScoredRecommendation]:
    """Score active perks using deterministic cold-start rules."""

    scored: list[ScoredRecommendation] = []
    for perk in available_perks:
        if not perk.is_active:
            continue
        if category is not None and perk.category != category:
            continue

        category_score = affinity_vector.get(perk.category, 0.05)
        quality = perk.quality_score or 0.5
        popularity = perk.popularity_score or 0.0
        is_affordable = perk.employee_price_cents <= budget_remaining_cents
        price_factor = 1.0 if is_affordable else 0.1

        final_score = (0.5 * category_score + 0.3 * quality + 0.2 * popularity)
        final_score *= price_factor

        scored.append(
            ScoredRecommendation(
                perk=perk,
                recommendation_score=round(final_score, 6),
                reason_code=f"AFFINITY_{perk.category.upper()}_HIGH",
                reason_text=f"Përputhet me preferencat e tua për {category_label(perk.category)}",
                is_affordable=is_affordable,
            )
        )

    scored.sort(key=lambda recommendation: recommendation.recommendation_score, reverse=True)
    return scored[:limit]

