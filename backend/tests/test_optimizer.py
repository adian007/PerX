"""Plan optimizer (PuLP knapsack) API tests."""

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
from app.models.perk import Perk
from app.models.provider import ProviderProfile
from app.models.selection import PerkSelection
from app.models.user import User
from app.services.optimizer.knapsack import solve_knapsack
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


async def _seed_optimizer_stack(
    db_session: AsyncSession,
    *,
    allocated_cents: int = 5000,
) -> tuple[User, list[Perk]]:
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
        organization_name="Optimize Corp",
        invite_code=f"OPT-{uuid.uuid4().hex[:4].upper()}",
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
        first_name="Opt",
        last_name="Tester",
        onboarding_completed=True,
        preferred_categories=[PerkCategory.wellness],
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
            allocated_cents=allocated_cents,
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
        company_name="OptFit",
        status=ProviderStatus.active,
    )
    db_session.add(provider)
    await db_session.flush()

    perk_specs = [
        ("Yoga Pass", 3000, 0.9),
        ("Gym Premium", 4000, 0.7),
        ("Meditation App", 2000, 0.8),
    ]
    perks: list[Perk] = []
    for name, price, _score in perk_specs:
        perk = Perk(
            provider_id=provider.id,
            name=name,
            slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
            description=name,
            category=PerkCategory.wellness,
            employee_price_cents=price,
            provider_cost_cents=price - 500,
            currency_code="ALL",
            is_active=True,
            quality_score=0.8,
            popularity_score=0.6,
        )
        db_session.add(perk)
        perks.append(perk)
    await db_session.flush()
    return employee_user, perks


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_solve_knapsack_unit():
    perks = [
        {"id": uuid.uuid4(), "price_cents": 3000, "score": 0.9, "name": "A"},
        {"id": uuid.uuid4(), "price_cents": 4000, "score": 0.7, "name": "B"},
        {"id": uuid.uuid4(), "price_cents": 2000, "score": 0.8, "name": "C"},
    ]
    result = solve_knapsack(perks, budget_cents=5000)
    assert result["status"] == "optimal"
    assert result["total_cost_cents"] == 5000
    assert len(result["approved_ids"]) == 2


@pytest.mark.asyncio
async def test_optimize_plan_returns_run(client: AsyncClient, db_session: AsyncSession):
    user, perks = await _seed_optimizer_stack(db_session, allocated_cents=5000)
    token = await _login(client, user.email)

    response = await client.post(
        "/api/v1/selections/optimize-plan",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_ids": [str(perk.id) for perk in perks]},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "optimal"
    assert data["budget_available_cents"] == 5000
    assert data["total_cost_cents"] == 5000
    assert "run_id" in data
    included = [row for row in data["approved_perks"] if row["included"]]
    assert len(included) == 2


@pytest.mark.asyncio
async def test_confirm_optimizer_creates_selections(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user, perks = await _seed_optimizer_stack(db_session, allocated_cents=5000)
    token = await _login(client, user.email)

    optimize_response = await client.post(
        "/api/v1/selections/optimize-plan",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_ids": [str(perk.id) for perk in perks]},
    )
    run_id = optimize_response.json()["data"]["run_id"]

    confirm_response = await client.post(
        f"/api/v1/selections/optimize-plan/{run_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert confirm_response.status_code == 201
    data = confirm_response.json()["data"]
    assert len(data["selection_ids"]) == 2
    assert data["budget_remaining_cents"] == 0

    selection_ids = [uuid.UUID(sid) for sid in data["selection_ids"]]
    selections = await db_session.scalars(
        select(PerkSelection).where(PerkSelection.id.in_(selection_ids))
    )
    assert len(list(selections.all())) == 2


@pytest.mark.asyncio
async def test_confirm_unknown_run(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_optimizer_stack(db_session)
    token = await _login(client, user.email)

    response = await client.post(
        f"/api/v1/selections/optimize-plan/{uuid.uuid4()}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"
