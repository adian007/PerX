"""Gamification API tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.database import get_db
from app.main import create_app
from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import PerkCategory, ProviderStatus, UserRole
from app.models.gamification import EmployeeGamification, JourneyProgress
from app.models.perk import Perk
from app.models.provider import ProviderProfile
from app.models.user import User
from app.utils.redis import reset_redis_for_tests


@pytest.fixture(autouse=True)
def memory_redis(monkeypatch):
    monkeypatch.setenv("REDIS_USE_MEMORY", "true")
    monkeypatch.setenv("ALLOW_DEMO_MODE", "false")


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


async def _seed_employee(db_session: AsyncSession) -> tuple[User, Perk]:
    employer_user = User(
        email=f"employer-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(employer_user)
    await db_session.flush()

    employer = EmployerOrganization(
        user_id=employer_user.id,
        organization_name="Game Corp",
        invite_code=f"GAME-{uuid.uuid4().hex[:4].upper()}",
        contact_name="HR",
    )
    db_session.add(employer)
    await db_session.flush()

    employee_user = User(
        email=f"employee-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employee,
        is_verified=True,
    )
    db_session.add(employee_user)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=employee_user.id,
        employer_id=employer.id,
        first_name="Game",
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

    provider_user = User(
        email=f"provider-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.provider,
        is_verified=True,
    )
    db_session.add(provider_user)
    await db_session.flush()

    provider = ProviderProfile(
        user_id=provider_user.id,
        company_name="GameFit",
        status=ProviderStatus.active,
    )
    db_session.add(provider)
    await db_session.flush()

    perk = Perk(
        provider_id=provider.id,
        name="Yoga Pass",
        slug=f"yoga-{uuid.uuid4().hex[:8]}",
        description="Monthly yoga",
        category=PerkCategory.wellness,
        employee_price_cents=3000,
        provider_cost_cents=2000,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(perk)
    await db_session.flush()
    return employee_user, perk


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_get_gamification_empty(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_employee(db_session)
    token = await _login(client, user.email)

    response = await client.get(
        "/api/v1/me/gamification",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["level"] == 1
    assert data["points_balance"] == 0
    assert data["completed_path_nodes"] == []
    assert data["unlocked_achievements"] == []
    assert data["quiz_progress"] == {}


@pytest.mark.asyncio
async def test_complete_journey_awards_points(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_employee(db_session)
    token = await _login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/me/journey/food/complete", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "food" in data["completed_path_nodes"]
    assert data["points_balance"] == 40
    assert "first-steps" in data["unlocked_achievements"]

    duplicate = await client.post("/api/v1/me/journey/food/complete", headers=headers)
    assert duplicate.json()["data"]["points_balance"] == 40


@pytest.mark.asyncio
async def test_save_quiz_score(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_employee(db_session)
    token = await _login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.put(
        "/api/v1/me/quiz/fitness",
        headers=headers,
        json={"score": 3, "total": 3},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["quiz_progress"]["fitness"] == 3
    assert "fitness" in data["completed_path_nodes"]
    assert data["points_balance"] == 70


@pytest.mark.asyncio
async def test_unlock_achievement(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_employee(db_session)
    token = await _login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/me/achievements/globe-trotter/unlock", headers=headers)
    assert response.status_code == 201
    assert "globe-trotter" in response.json()["data"]["unlocked_achievements"]


@pytest.mark.asyncio
async def test_submit_review(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee(db_session)
    token = await _login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/me/reviews",
        headers=headers,
        json={"perk_id": str(perk.id), "rating": 5, "feedback": "Great"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["perk_id"] == str(perk.id)
    assert data["points_balance"] == 25


@pytest.mark.asyncio
async def test_record_daily_visit(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_employee(db_session)
    token = await _login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.patch(
        "/api/v1/me/gamification",
        headers=headers,
        json={"record_daily_visit": True},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["streak_days"] == 1
    assert data["points_balance"] == 10
    assert data["last_active_date"] is not None


@pytest.mark.asyncio
async def test_wishlist_awards_gamification(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee(db_session)
    token = await _login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(f"/api/v1/me/wishlist/{perk.id}", headers=headers)

    gamification = await db_session.get(EmployeeGamification, user.id)
    assert gamification is not None
    assert gamification.points == 15


@pytest.mark.asyncio
async def test_quick_add_awards_gamification(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee(db_session)
    token = await _login(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/selections/quick-add",
        headers=headers,
        json={"perk_id": str(perk.id)},
    )
    assert response.status_code == 200

    gamification = await db_session.get(EmployeeGamification, user.id)
    assert gamification is not None
    assert gamification.points == 75
    assert gamification.xp == 30

    journey_rows = await db_session.scalars(
        select(JourneyProgress).where(JourneyProgress.user_id == user.id)
    )
    assert len(list(journey_rows.all())) >= 1
