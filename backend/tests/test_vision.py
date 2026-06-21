"""Vision job API tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.config import get_settings
from app.database import get_db
from app.main import create_app
from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import UserRole
from app.models.user import User
from app.utils.redis import reset_redis_for_tests


@pytest.fixture(autouse=True)
def memory_redis(monkeypatch):
    monkeypatch.setenv("REDIS_USE_MEMORY", "true")
    monkeypatch.setenv("ALLOW_DEMO_MODE", "false")
    monkeypatch.setenv("CV_ENABLED", "false")


@pytest.fixture(autouse=True)
async def reset_rate_limits():
    await reset_redis_for_tests()
    yield
    await reset_redis_for_tests()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def _seed_employee(db_session: AsyncSession, *, suffix: str = "a") -> User:
    employer_user = User(
        email=f"vision-employer-{suffix}-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(employer_user)
    await db_session.flush()

    employer = EmployerOrganization(
        user_id=employer_user.id,
        organization_name=f"Vision Corp {suffix}",
        invite_code=f"VIS-{suffix.upper()}-{uuid.uuid4().hex[:4].upper()}",
        contact_name="HR",
    )
    db_session.add(employer)
    await db_session.flush()

    employee_user = User(
        email=f"vision-employee-{suffix}-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employee,
        is_verified=True,
    )
    db_session.add(employee_user)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=employee_user.id,
        employer_id=employer.id,
        first_name=f"Vision{suffix.upper()}",
        last_name="Tester",
        onboarding_completed=True,
    )
    db_session.add(employee)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    db_session.add(
        BudgetAllocation(
            employer_id=employer.id,
            employee_id=employee.id,
            period_year=now.year,
            period_month=now.month,
            allocated_cents=10000,
            currency_code="ALL",
        )
    )
    await db_session.flush()
    return employee_user


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_vision_job_uses_backend_mock_when_cv_disabled(
    client: AsyncClient, db_session: AsyncSession
):
    user = await _seed_employee(db_session)
    token = await _login(client, user.email)

    response = await client.post(
        "/api/v1/vision/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"task": "lifestyle", "image_url": "https://example.com/photo.jpg"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["source"] == "backend-mock"
    assert body["job"]["status"] == "completed"
    assert body["job"]["result"]["mock"] is True


@pytest.mark.asyncio
async def test_vision_payload_too_large(client: AsyncClient, db_session: AsyncSession):
    user = await _seed_employee(db_session)
    token = await _login(client, user.email)
    limit = get_settings().cv_max_image_bytes
    oversized = "A" * (limit + 1)

    response = await client.post(
        "/api/v1/vision/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"task": "ocr", "image_base64": oversized},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "VISION_PAYLOAD_TOO_LARGE"


@pytest.mark.asyncio
async def test_vision_job_other_user_gets_404(client: AsyncClient, db_session: AsyncSession):
    owner = await _seed_employee(db_session, suffix="owner")
    other = await _seed_employee(db_session, suffix="other")
    owner_token = await _login(client, owner.email)
    other_token = await _login(client, other.email)

    create_response = await client.post(
        "/api/v1/vision/jobs",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"task": "receipt", "metadata": {"source": "test"}},
    )
    assert create_response.status_code == 200
    job_id = create_response.json()["data"]["job"]["id"]

    get_response = await client.get(
        f"/api/v1/vision/jobs/{job_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "VISION_JOB_NOT_FOUND"
