"""Integration tests for layered backend + security wiring."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.database import get_db
from app.main import create_app
from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import PerkCategory, ProviderStatus, UserRole
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


async def _seed_employee_stack(
    db_session: AsyncSession,
) -> tuple[User, EmployeeProfile, Perk]:
    employer_user = User(
        email=f"employer-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
        locale="sq-AL",
    )
    db_session.add(employer_user)
    await db_session.flush()

    employer = EmployerOrganization(
        user_id=employer_user.id,
        organization_name="Demo Corp",
        invite_code=f"DEMO-{uuid.uuid4().hex[:4].upper()}",
        contact_name="HR",
        default_currency_code="ALL",
    )
    db_session.add(employer)
    await db_session.flush()

    employee_user = User(
        email=f"employee-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employee,
        is_verified=True,
        locale="sq-AL",
    )
    db_session.add(employee_user)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=employee_user.id,
        employer_id=employer.id,
        first_name="Mira",
        last_name="Demo",
        onboarding_completed=True,
        affinity_vector={"fitness": 0.8, "wellness": 0.6},
        interaction_count=0,
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
            spent_cents=2000,
            pending_cents=1000,
            currency_code="ALL",
        )
    )

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
        company_name="FlowFit",
        status=ProviderStatus.active,
    )
    db_session.add(provider)
    await db_session.flush()

    perk = Perk(
        provider_id=provider.id,
        name="Yoga Pass",
        slug=f"yoga-{uuid.uuid4().hex[:8]}",
        description="Monthly yoga membership",
        short_description="Unlimited yoga",
        category=PerkCategory.wellness,
        employee_price_cents=4500,
        provider_cost_cents=3500,
        is_active=True,
        is_featured=True,
    )
    db_session.add(perk)
    await db_session.flush()
    return employee_user, employee, perk


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_recommendations_require_auth_when_demo_disabled(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await _seed_employee_stack(db_session)
    response = await client.get("/api/v1/recommendations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_employee_gets_db_recommendations(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")
    user, _, _ = await _seed_employee_stack(db_session)
    token = await _login(client, user.email)

    response = await client.get(
        "/api/v1/recommendations",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 5},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["mode"] == "cold_start"
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_employee_me_and_budget(client: AsyncClient, db_session: AsyncSession):
    user, _, _ = await _seed_employee_stack(db_session)
    token = await _login(client, user.email)

    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == user.email
    assert me.json()["data"]["employer"]["organization_name"] == "Demo Corp"

    budget = await client.get(
        "/api/v1/me/budget",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert budget.status_code == 200
    data = budget.json()["data"]
    assert data["allocated_cents"] == 10000
    assert data["remaining_cents"] == 7000


@pytest.mark.asyncio
async def test_catalog_excludes_pending_provider_perks(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user, _, visible = await _seed_employee_stack(db_session)

    pending_provider_user = User(
        email=f"pending-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.provider,
        is_verified=True,
    )
    db_session.add(pending_provider_user)
    await db_session.flush()
    pending_provider = ProviderProfile(
        user_id=pending_provider_user.id,
        company_name="Pending Co",
        status=ProviderStatus.pending_review,
    )
    db_session.add(pending_provider)
    await db_session.flush()
    hidden = Perk(
        provider_id=pending_provider.id,
        name="Hidden Gym",
        slug=f"hidden-{uuid.uuid4().hex[:8]}",
        description="Should not appear",
        category=PerkCategory.fitness,
        employee_price_cents=2000,
        provider_cost_cents=1500,
        is_active=True,
    )
    db_session.add(hidden)
    await db_session.flush()

    token = await _login(client, user.email)
    response = await client.get(
        "/api/v1/perks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]["perks"]}
    assert str(visible.id) in ids
    assert str(hidden.id) not in ids


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
