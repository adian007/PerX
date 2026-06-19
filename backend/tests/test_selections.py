"""Quick-add selection and budget atomic decrement tests."""

from __future__ import annotations

import asyncio
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
from app.utils.redis import RedisClient, get_redis_client, reset_redis_for_tests


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


async def _seed_stack(
    db_session: AsyncSession,
    *,
    allocated_cents: int = 10000,
    spent_cents: int = 0,
    pending_cents: int = 0,
    perk_price: int = 4500,
) -> tuple[User, EmployeeProfile, Perk, BudgetAllocation]:
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
        organization_name="Budget Corp",
        invite_code=f"BUD-{uuid.uuid4().hex[:4].upper()}",
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
    )
    db_session.add(employee_user)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=employee_user.id,
        employer_id=employer.id,
        first_name="Ana",
        last_name="Test",
        onboarding_completed=True,
    )
    db_session.add(employee)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    allocation = BudgetAllocation(
        employer_id=employer.id,
        employee_id=employee.id,
        period_year=now.year,
        period_month=now.month,
        allocated_cents=allocated_cents,
        spent_cents=spent_cents,
        pending_cents=pending_cents,
        currency_code="ALL",
    )
    db_session.add(allocation)
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
        company_name="FlowFit",
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
        employee_price_cents=perk_price,
        provider_cost_cents=3500,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(perk)
    await db_session.flush()
    return employee_user, employee, perk, allocation


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_quick_add_success(client: AsyncClient, db_session: AsyncSession):
    user, _, perk, _ = await _seed_stack(db_session, allocated_cents=10000)
    token = await _login(client, user.email)

    response = await client.post(
        "/api/v1/selections/quick-add",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_id": str(perk.id)},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "pending_approval"
    assert data["budget_remaining_cents"] == 10000 - perk.employee_price_cents
    assert "provider_cost_cents" not in str(data)


@pytest.mark.asyncio
async def test_quick_add_insufficient_budget(client: AsyncClient, db_session: AsyncSession):
    user, _, perk, _ = await _seed_stack(
        db_session,
        allocated_cents=3000,
        perk_price=4500,
    )
    token = await _login(client, user.email)

    response = await client.post(
        "/api/v1/selections/quick-add",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_id": str(perk.id)},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INSUFFICIENT_BUDGET"


@pytest.mark.asyncio
async def test_quick_add_requires_employee_role(client: AsyncClient, db_session: AsyncSession):
    employer_user = User(
        email=f"employer-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(employer_user)
    await db_session.flush()
    db_session.add(
        EmployerOrganization(
            user_id=employer_user.id,
            organization_name="Only Employer",
            invite_code=f"EMP-{uuid.uuid4().hex[:4].upper()}",
            contact_name="HR",
        )
    )
    await db_session.flush()

    token = await _login(client, employer_user.email)
    response = await client.post(
        "/api/v1/selections/quick-add",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_id": str(uuid.uuid4())},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_concurrent_quick_add_respects_budget(db_session: AsyncSession):
    """Two parallel decrements against a budget that fits only one selection."""

    user, employee, perk, allocation = await _seed_stack(
        db_session,
        allocated_cents=5000,
        perk_price=4500,
    )
    await reset_redis_for_tests()
    redis = await get_redis_client()

    from app.services.budget import InsufficientBudgetError, atomic_decrement_budget, ensure_budget_cached

    await ensure_budget_cached(redis, allocation)

    async def attempt() -> int:
        try:
            return await atomic_decrement_budget(redis, allocation, 4500)
        except InsufficientBudgetError:
            return -1

    results = await asyncio.gather(attempt(), attempt())
    successes = [value for value in results if value >= 0]
    failures = [value for value in results if value < 0]

    assert len(successes) == 1
    assert len(failures) == 1
    assert successes[0] == 500


@pytest.mark.asyncio
async def test_get_my_selections_after_quick_add(client: AsyncClient, db_session: AsyncSession):
    user, _, perk, _ = await _seed_stack(db_session)
    token = await _login(client, user.email)

    await client.post(
        "/api/v1/selections/quick-add",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_id": str(perk.id)},
    )

    response = await client.get(
        "/api/v1/me/selections",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 1
    assert rows[0]["status"] == "pending_approval"
    assert "provider_cost_cents" not in rows[0]["perk"]
