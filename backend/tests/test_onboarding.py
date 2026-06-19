from fastapi.testclient import TestClient

from app.main import create_app
from app.services.recommendation.onboarding import complete_onboarding
from app.utils.ollama import EXPLANATION_STORE


def test_complete_onboarding_service_returns_affinity():
    result = complete_onboarding(
        lifestyle_tags=["cyclist", "remote_worker"],
        preferred_categories=["fitness", "wellness"],
        budget_sensitivity="medium",
        wellness_priority=8,
        family_situation="couple",
    )

    assert result.onboarding_completed is True
    assert result.affinity_vector["fitness"] > 0.0
    assert len(result.top_categories) >= 1


def test_onboarding_api_returns_expected_shape(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    monkeypatch.setenv("ALLOW_DEMO_MODE", "true")
    monkeypatch.setenv("REDIS_USE_MEMORY", "true")
    EXPLANATION_STORE.clear()
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/me/onboarding",
        json={
            "lifestyle_tags": ["cyclist", "yogi"],
            "preferred_categories": ["fitness", "wellness"],
            "budget_sensitivity": "medium",
            "wellness_priority": 8,
            "family_situation": "couple",
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["onboarding_completed"] is True
    assert body["explanation_pending"] is True
    assert body["explanation"] is None
    assert body["affinity_vector"]["fitness"] > 0.0


def test_onboarding_explanation_poll(monkeypatch):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    monkeypatch.setenv("ALLOW_DEMO_MODE", "true")
    monkeypatch.setenv("REDIS_USE_MEMORY", "true")
    EXPLANATION_STORE.clear()
    client = TestClient(create_app())

    client.post(
        "/api/v1/me/onboarding",
        json={
            "lifestyle_tags": ["foodie"],
            "preferred_categories": ["food"],
            "budget_sensitivity": "medium",
            "wellness_priority": 5,
            "family_situation": "single",
        },
    )

    # Background task runs synchronously in TestClient
    response = client.get("/api/v1/me/onboarding/explanation")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["ready"] is True
    assert body["explanation"] is not None
    assert "food" in body["explanation"].lower()
