import pytest

from app.models.recommendation import Perk, Provider
from app.services.recommendation.cold_start import (
    compute_affinity_vector,
    score_cold_start_recommendations,
)


def test_compute_affinity_vector_prr_validation_example():
    affinity = compute_affinity_vector(
        lifestyle_tags=["cyclist", "yogi"],
        preferred_categories=["fitness"],
        budget_sensitivity="medium",
        wellness_priority=8,
        family_situation="couple",
    )

    assert affinity["fitness"] > 0.6
    assert affinity["wellness"] > 0.6


def test_compute_affinity_vector_is_deterministic():
    kwargs = {
        "lifestyle_tags": ["foodie"],
        "preferred_categories": ["food"],
        "budget_sensitivity": "high",
        "wellness_priority": 5,
        "family_situation": "single",
    }
    first = compute_affinity_vector(**kwargs)
    second = compute_affinity_vector(**kwargs)
    assert first == second


def test_unaffordable_perk_gets_budget_penalty():
    provider = Provider(id="provider-1", company_name="FlowFit")
    expensive = Perk(
        id="perk-expensive",
        name="Premium Travel",
        category="travel",
        short_description="Luxury travel",
        image_url=None,
        employee_price_cents=20000,
        provider=provider,
        quality_score=0.9,
        popularity_score=0.9,
    )
    affordable = Perk(
        id="perk-cheap",
        name="Bike Pass",
        category="transport",
        short_description="Bike share",
        image_url=None,
        employee_price_cents=1000,
        provider=provider,
        quality_score=0.5,
        popularity_score=0.5,
    )

    recommendations = score_cold_start_recommendations(
        affinity_vector={"travel": 0.9, "transport": 0.2},
        available_perks=[expensive, affordable],
        budget_remaining_cents=5000,
    )

    expensive_rec = next(
        recommendation
        for recommendation in recommendations
        if recommendation.perk.id == "perk-expensive"
    )
    affordable_rec = next(
        recommendation
        for recommendation in recommendations
        if recommendation.perk.id == "perk-cheap"
    )

    assert expensive_rec.is_affordable is False
    assert affordable_rec.is_affordable is True
    assert expensive_rec.recommendation_score < affordable_rec.recommendation_score


def test_category_filter_and_limit():
    provider = Provider(id="provider-1", company_name="FlowFit")
    perks = [
        Perk(
            id="perk-wellness",
            name="Yoga",
            category="wellness",
            short_description="Yoga",
            image_url=None,
            employee_price_cents=1000,
            provider=provider,
        ),
        Perk(
            id="perk-fitness",
            name="Gym",
            category="fitness",
            short_description="Gym",
            image_url=None,
            employee_price_cents=1000,
            provider=provider,
        ),
    ]

    recommendations = score_cold_start_recommendations(
        affinity_vector={"wellness": 0.9, "fitness": 0.4},
        available_perks=perks,
        budget_remaining_cents=5000,
        category="wellness",
        limit=1,
    )

    assert len(recommendations) == 1
    assert recommendations[0].perk.category == "wellness"
