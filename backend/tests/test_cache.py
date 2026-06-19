import asyncio
import time

from fastapi import BackgroundTasks

from app.services.recommendation.cache import InMemoryRecommendationCache
from app.services.recommendation.engine import build_recommendation_payload
from app.models.recommendation import EmployeeProfile, Perk, Provider


def _employee() -> EmployeeProfile:
    return EmployeeProfile(
        id="employee-cache",
        first_name="Cache",
        interaction_count=9,
        lifestyle_tags=["yogi"],
        preferred_categories=["wellness"],
        budget_sensitivity="medium",
        wellness_priority=8,
        family_situation="single",
    )


def _perks() -> list[Perk]:
    provider = Provider(id="provider-1", company_name="FlowFit")
    return [
        Perk(
            id="perk-1",
            name="Yoga Pass",
            category="wellness",
            short_description="Yoga classes",
            image_url=None,
            employee_price_cents=1000,
            provider=provider,
            quality_score=0.9,
            popularity_score=0.8,
        )
    ]


def test_cache_miss_then_hit(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    cache = InMemoryRecommendationCache()

    first = asyncio.run(
        build_recommendation_payload(
            employee=_employee(),
            available_perks=_perks(),
            background_tasks=BackgroundTasks(),
            budget_remaining_cents=5000,
            cache=cache,
        )
    )
    second = asyncio.run(
        build_recommendation_payload(
            employee=_employee(),
            available_perks=_perks(),
            background_tasks=BackgroundTasks(),
            budget_remaining_cents=5000,
            cache=cache,
        )
    )

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["cache_age_seconds"] >= 0


def test_refresh_bypasses_cache():
    cache = InMemoryRecommendationCache()

    asyncio.run(
        build_recommendation_payload(
            employee=_employee(),
            available_perks=_perks(),
            background_tasks=BackgroundTasks(),
            budget_remaining_cents=5000,
            cache=cache,
        )
    )
    refreshed = asyncio.run(
        build_recommendation_payload(
            employee=_employee(),
            available_perks=_perks(),
            background_tasks=BackgroundTasks(),
            budget_remaining_cents=5000,
            refresh=True,
            cache=cache,
        )
    )

    assert refreshed["cached"] is False


def test_cache_expires_after_ttl():
    cache = InMemoryRecommendationCache()

    asyncio.run(
        build_recommendation_payload(
            employee=_employee(),
            available_perks=_perks(),
            background_tasks=BackgroundTasks(),
            budget_remaining_cents=5000,
            cache=cache,
        )
    )

    cache_key = next(iter(cache._entries))
    entry = cache._entries[cache_key]
    entry.expires_at = time.monotonic() - 1

    cached = asyncio.run(cache.get(cache_key))
    assert cached is None
