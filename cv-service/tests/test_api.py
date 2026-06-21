"""FastAPI endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import bgr_to_base64, solid_rgb

client = TestClient(app)


def test_health_lists_tasks():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["tasks"]) == {"lifestyle", "receipt", "ocr", "catalog_tag", "visual_search"}


def test_analyze_all_tasks():
    image_b64 = bgr_to_base64(solid_rgb((100, 150, 200)))
    for task in ("lifestyle", "receipt", "ocr", "catalog_tag", "visual_search"):
        response = client.post("/analyze", json={"task": task, "image_base64": image_b64})
        assert response.status_code == 200, task
        body = response.json()
        assert body["task"] == task
        assert "result" in body
        assert "technique" in body["meta"]


def test_analyze_rejects_unknown_task():
    response = client.post("/analyze", json={"task": "unknown", "image_base64": "abc"})
    assert response.status_code == 422 or response.status_code == 400


def test_analyze_requires_key_when_configured(monkeypatch):
    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "internal_key", "test-secret")
    protected = TestClient(app)

    response = protected.post("/analyze", json={"task": "ocr", "image_base64": "abc"})
    assert response.status_code == 403

    authed = protected.post(
        "/analyze",
        json={"task": "ocr", "image_base64": bgr_to_base64(solid_rgb((100, 150, 200)))},
        headers={"X-CV-Internal-Key": "test-secret"},
    )
    assert authed.status_code == 200
