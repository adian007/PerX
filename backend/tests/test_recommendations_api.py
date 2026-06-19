import asyncio
import time

from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.recommendation import EmployeeProfile, Perk, Provider
from app.services.recommendation.engine import build_recommendation_payload
from app.utils.ollama import generate_or_fallback_explanation


def test_recommendations_endpoint_returns_enveloped_response(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    client = TestClient(create_app())

    response = client.get("/api/v1/recommendations", params={"limit": 2, "demo": "cold"})

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert body["data"]["mode"] == "cold_start"
    assert body["data"]["total"] == 2


def test_warm_demo_endpoint_can_return_score_breakdown(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/recommendations",
        params={"demo": "warm", "include_score_breakdown": True, "limit": 1},
    )

    assert response.status_code == 200
    perk = response.json()["data"]["perks"][0]
    assert response.json()["data"]["mode"] == "warm"
    assert perk["score_breakdown"]["final_score"] == perk["recommendation_score"]


def test_second_request_returns_cached_response(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    client = TestClient(create_app())

    first = client.get("/api/v1/recommendations", params={"demo": "warm", "limit": 3})
    second = client.get("/api/v1/recommendations", params={"demo": "warm", "limit": 3})

    assert first.json()["data"]["cached"] is False
    assert second.json()["data"]["cached"] is True
    assert second.json()["data"]["cache_age_seconds"] >= 0


def test_recommendation_explanation_endpoint(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    client = TestClient(create_app())

    client.get("/api/v1/recommendations", params={"demo": "cold", "limit": 1})
    response = client.get("/api/v1/recommendations/explanation", params={"demo": "cold"})

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["ready"] is True
    assert body["explanation"] is not None


def test_ollama_health_endpoint(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    client = TestClient(create_app())

    response = client.get("/api/v1/internal/ollama-health")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["reachable"] is False
    assert body["model_available"] is False


def _employee() -> EmployeeProfile:
    return EmployeeProfile(
        id="employee-1",
        first_name="Ada",
        interaction_count=0,
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


def test_ollama_down_recommendation_returns_with_fallback(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")

    payload = asyncio.run(
        build_recommendation_payload(
            employee=_employee(),
            available_perks=_perks(),
            background_tasks=BackgroundTasks(),
            budget_remaining_cents=5000,
        )
    )

    assert payload["total"] == 1
    assert payload["explanation_pending"] is True
    assert "wellness" in payload["explanation"].lower()

    explanation = asyncio.run(
        generate_or_fallback_explanation(
            affinity_vector={"wellness": 0.9},
            top_categories=["wellness"],
            employee_name="Ada",
        )
    )
    assert "wellness" in explanation.lower()


def test_recommendation_response_does_not_wait_on_llm(monkeypatch):
    async def slow_background_task(*args, **kwargs):
        await asyncio.sleep(5)

    monkeypatch.setattr(
        "app.services.recommendation.engine.generate_and_store_explanation",
        slow_background_task,
    )

    started_at = time.perf_counter()
    payload = asyncio.run(
        build_recommendation_payload(
            employee=_employee(),
            available_perks=_perks(),
            background_tasks=BackgroundTasks(),
            budget_remaining_cents=5000,
        )
    )
    elapsed = time.perf_counter() - started_at

    assert payload["total"] == 1
    assert elapsed < 0.05
