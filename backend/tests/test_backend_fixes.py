"""Tests for backend fixes: formatting, employer insights, push subscription, onboarding DB."""

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
from app.models.user import User
from app.utils.formatting import format_money
from app.utils.ollama import generate_and_store_explanation
from app.utils.redis import reset_redis_for_tests


@pytest.fixture(autouse=True)
def memory_redis(monkeypatch):
    monkeypatch.setenv("REDIS_USE_MEMORY", "true")
    monkeypatch.setenv("ALLOW_DEMO_MODE", "false")
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")


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


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


async def _seed_employer_stack(
    db_session: AsyncSession,
    *,
    allocated_cents: int = 50000,
    spent_cents: int = 10000,
    pending_cents: int = 3500,
) -> tuple[User, User, EmployeeProfile, EmployerOrganization, Perk]:
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
        organization_name="Insights Corp",
        invite_code=f"INS-{uuid.uuid4().hex[:4].upper()}",
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
        first_name="Eli",
        last_name="Worker",
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
            allocated_cents=allocated_cents,
            spent_cents=spent_cents,
            pending_cents=pending_cents,
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
        company_name="WellCo",
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
        employee_price_cents=4500,
        provider_cost_cents=3500,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(perk)
    await db_session.flush()

    return employer_user, employee_user, employee, employer, perk


def test_format_money_all_sq_al():
    assert format_money(123456, currency_code="ALL", locale="sq-AL") == "1.234,56 Lek"
    assert format_money(50000, currency_code="ALL", locale="sq-AL") == "500 Lek"


@pytest.mark.asyncio
async def test_employer_insights(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, _, _, perk = await _seed_employer_stack(db_session)

    employee_token = await _login(client, employee_user.email)
    add_response = await client.post(
        "/api/v1/selections/quick-add",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"perk_id": str(perk.id)},
    )
    assert add_response.status_code == 200

    employer_token = await _login(client, employer_user.email)
    response = await client.get(
        "/api/v1/employer/insights",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["currency_code"] == "ALL"
    assert data["employee_count"] == 1
    assert data["total_allocated_cents"] == 50000
    assert "Lek" in data["allocated_formatted"]
    assert data["pending_approval_count"] >= 1


@pytest.mark.asyncio
async def test_push_subscription_persists_on_user(client: AsyncClient, db_session: AsyncSession):
    employer_user, _, _, _, _ = await _seed_employer_stack(db_session)
    token = await _login(client, employer_user.email)

    response = await client.post(
        "/api/v1/auth/push-subscription",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "push_endpoint": "https://push.example/endpoint",
            "push_p256dh": "p256dh-key",
            "push_auth": "auth-secret",
        },
    )
    assert response.status_code == 204

    await db_session.refresh(employer_user)
    assert employer_user.push_endpoint == "https://push.example/endpoint"
    assert employer_user.push_p256dh == "p256dh-key"
    assert employer_user.push_auth == "auth-secret"


@pytest.mark.asyncio
async def test_onboarding_explanation_persisted_to_db(
    db_session: AsyncSession,
    monkeypatch,
):
    monkeypatch.setenv("OLLAMA_FORCE_FAIL", "true")

    class _SessionCtx:
        def __init__(self, session: AsyncSession) -> None:
            self._session = session

        async def __aenter__(self) -> AsyncSession:
            return self._session

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "app.utils.ollama.AsyncSessionLocal",
        lambda: _SessionCtx(db_session),
    )

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
        organization_name="Onboard Corp",
        invite_code=f"ONB-{uuid.uuid4().hex[:4].upper()}",
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
        last_name="Demo",
        onboarding_completed=False,
    )
    db_session.add(employee)
    await db_session.flush()

    await generate_and_store_explanation(
        str(employee.id),
        {"fitness": 0.9, "wellness": 0.4},
        ["fitness"],
        "Ana",
    )

    refreshed = await db_session.scalar(
        select(EmployeeProfile).where(EmployeeProfile.id == employee.id)
    )
    assert refreshed is not None
    assert refreshed.welcome_explanation is not None
    assert "fitness" in refreshed.welcome_explanation.lower()
