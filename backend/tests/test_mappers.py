import pytest

from app.services.recommendation.mappers import (
    employee_profile_from_row,
    perk_from_row,
    ucb_counts_from_interactions,
)


def test_employee_profile_from_row_maps_db_columns():
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "first_name": "John",
        "interaction_count": 9,
        "recommender_mode": "cold_start",
        "lifestyle_tags": ["cyclist"],
        "preferred_categories": ["fitness"],
        "budget_sensitivity": "medium",
        "wellness_priority": 8,
        "family_situation": "couple",
        "affinity_vector": {"fitness": 0.8},
    }

    profile = employee_profile_from_row(row)
    assert profile.id == row["id"]
    assert profile.interaction_count == 9
    assert profile.affinity_vector == {"fitness": 0.8}


def test_perk_from_row_maps_provider_fields():
    perk_row = {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Yoga Pass",
        "category": "wellness",
        "short_description": "Yoga classes",
        "image_url": None,
        "employee_price_cents": 4500,
        "tags": ["yoga"],
        "is_active": True,
        "is_featured": False,
        "popularity_score": 0.7,
        "quality_score": 0.9,
        "collaborative_score": 0.72,
    }
    provider_row = {
        "id": "33333333-3333-3333-3333-333333333333",
        "company_name": "FlowFit",
        "logo_url": "https://example.test/logo.png",
        "avg_rating": 4.7,
    }

    perk = perk_from_row(perk_row, provider_row)
    assert perk.name == "Yoga Pass"
    assert perk.provider.company_name == "FlowFit"
    assert perk.collaborative_score == pytest.approx(0.72)


def test_ucb_counts_from_interactions_counts_recommendation_views():
    interactions = [
        {"perk_id": "perk-a", "recommendation_rank": 1},
        {"perk_id": "perk-a", "recommendation_rank": 2},
        {"perk_id": "perk-b", "recommendation_rank": 3},
        {"perk_id": "perk-c", "recommendation_rank": None},
    ]

    counts = ucb_counts_from_interactions(interactions)
    assert counts == {"perk-a": 2, "perk-b": 1}
