import pytest

from app.models.recommendation import Perk, Provider
from app.services.recommendation.hybrid import (
    combine_scores,
    compute_warm_recommendations,
    ucb_bonus,
)


def test_warm_mode_final_score_math_is_weighted_correctly():
    assert combine_scores(0.8, 0.6, 0.5) == pytest.approx(0.66)


def test_warm_recommendation_includes_score_breakdown():
    provider = Provider(id="provider-1", company_name="FlowFit")
    perk = Perk(
        id="perk-1",
        name="Yoga",
        category="wellness",
        short_description="Yoga classes",
        image_url=None,
        employee_price_cents=1000,
        provider=provider,
    )

    recommendations = compute_warm_recommendations(
        affinity_vector={"wellness": 0.75},
        available_perks=[perk],
        budget_remaining_cents=5000,
        ucb_counts={},
        cf_scores={"perk-1": 0.5},
    )

    recommendation = recommendations[0]
    assert recommendation.recommendation_score == pytest.approx(0.7)
    assert recommendation.score_breakdown is not None
    assert recommendation.score_breakdown.content_score == pytest.approx(0.75)
    assert recommendation.score_breakdown.cf_score == pytest.approx(0.5)
    assert recommendation.score_breakdown.ucb_bonus == pytest.approx(1.0)
    assert recommendation.score_breakdown.final_score == pytest.approx(0.7)


def test_never_shown_perk_gets_max_ucb_bonus():
    assert ucb_bonus("perk-new", {}) == pytest.approx(1.0)


def test_shown_perk_gets_lower_ucb_bonus():
    assert ucb_bonus("perk-seen", {"perk-seen": 5}) < 1.0


def test_cf_scores_dict_takes_precedence_over_perk_collaborative_score():
    provider = Provider(id="provider-1", company_name="FlowFit")
    perk = Perk(
        id="perk-1",
        name="Yoga",
        category="wellness",
        short_description="Yoga classes",
        image_url=None,
        employee_price_cents=1000,
        provider=provider,
        collaborative_score=0.1,
    )

    with_dict = compute_warm_recommendations(
        affinity_vector={"wellness": 0.5},
        available_perks=[perk],
        budget_remaining_cents=5000,
        ucb_counts={"perk-1": 1},
        cf_scores={"perk-1": 0.9},
        limit=1,
    )
    without_dict = compute_warm_recommendations(
        affinity_vector={"wellness": 0.5},
        available_perks=[perk],
        budget_remaining_cents=5000,
        ucb_counts={"perk-1": 1},
        cf_scores=None,
        limit=1,
    )

    assert with_dict[0].score_breakdown.cf_score == pytest.approx(0.9)
    assert without_dict[0].score_breakdown.cf_score == pytest.approx(0.1)


def test_over_budget_perk_score_is_penalized():
    provider = Provider(id="provider-1", company_name="FlowFit")
    perk = Perk(
        id="perk-1",
        name="Luxury Travel",
        category="travel",
        short_description="Travel",
        image_url=None,
        employee_price_cents=20000,
        provider=provider,
        collaborative_score=0.8,
    )

    affordable = compute_warm_recommendations(
        affinity_vector={"travel": 0.8},
        available_perks=[perk],
        budget_remaining_cents=50000,
        ucb_counts={},
        cf_scores={"perk-1": 0.8},
        limit=1,
    )[0]
    penalized = compute_warm_recommendations(
        affinity_vector={"travel": 0.8},
        available_perks=[perk],
        budget_remaining_cents=5000,
        ucb_counts={},
        cf_scores={"perk-1": 0.8},
        limit=1,
    )[0]

    assert penalized.is_affordable is False
    assert penalized.recommendation_score == pytest.approx(
        affordable.recommendation_score * 0.1
    )


def test_category_filter_limits_results():
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

    recommendations = compute_warm_recommendations(
        affinity_vector={"wellness": 0.9, "fitness": 0.4},
        available_perks=perks,
        budget_remaining_cents=5000,
        ucb_counts={},
        category="wellness",
        limit=1,
    )

    assert len(recommendations) == 1
    assert recommendations[0].perk.category == "wellness"
