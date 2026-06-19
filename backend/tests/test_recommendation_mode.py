from app.services.recommendation.mode import determine_recommender_mode


def test_threshold_minus_one_gets_cold_start_mode():
    assert (
        determine_recommender_mode(
            interaction_count=9,
            current_mode="cold_start",
            warm_threshold=10,
        )
        == "cold_start"
    )


def test_threshold_gets_warm_mode():
    assert (
        determine_recommender_mode(
            interaction_count=10,
            current_mode="cold_start",
            warm_threshold=10,
        )
        == "warm"
    )


def test_warm_mode_does_not_downgrade():
    assert (
        determine_recommender_mode(
            interaction_count=0,
            current_mode="warm",
            warm_threshold=10,
        )
        == "warm"
    )

