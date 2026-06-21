"""Interaction logging API tests."""

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
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import InteractionType, PerkCategory, ProviderStatus, UserRole
from app.models.perk import Perk, PerkInteraction
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


async def _seed_employee_perk(db_session: AsyncSession) -> tuple[User, Perk]:
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
        organization_name="Interact Corp",
        invite_code=f"INT-{uuid.uuid4().hex[:4].upper()}",
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
        first_name="Log",
        last_name="Tester",
        onboarding_completed=True,
    )
    db_session.add(employee)
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
        company_name="InteractFit",
        status=ProviderStatus.active,
    )
    db_session.add(provider)
    await db_session.flush()

    perk = Perk(
        provider_id=provider.id,
        name="Coffee Club",
        slug=f"coffee-{uuid.uuid4().hex[:8]}",
        description="Monthly coffee",
        category=PerkCategory.food,
        employee_price_cents=1500,
        provider_cost_cents=1000,
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
async def test_log_single_interaction(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_perk(db_session)
    token = await _login(client, user.email)

    response = await client.post(
        "/api/v1/interactions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "perk_id": str(perk.id),
            "type": "view",
            "recommendation_rank": 2,
            "page_context": "home",
            "session_id": "sess_test",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["logged"] is True

    rows = await db_session.scalars(
        select(PerkInteraction).where(PerkInteraction.perk_id == perk.id)
    )
    interaction = list(rows.all())[0]
    assert interaction.interaction_type == InteractionType.view
    assert interaction.recommendation_rank == 2


@pytest.mark.asyncio
async def test_log_interaction_unknown_perk(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_employee_perk(db_session)
    token = await _login(client, user.email)

    response = await client.post(
        "/api/v1/interactions",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_id": str(uuid.uuid4()), "type": "click"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PERK_NOT_FOUND"


@pytest.mark.asyncio
async def test_log_interaction_strict_validation(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_perk(db_session)
    token = await _login(client, user.email)

    response = await client.post(
        "/api/v1/interactions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "perk_id": str(perk.id),
            "type": "view",
            "extra_field": "not_allowed",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_log_interactions_batch(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_perk(db_session)
    employee = await db_session.scalar(
        select(EmployeeProfile).where(EmployeeProfile.user_id == user.id)
    )
    assert employee is not None
    token = await _login(client, user.email)
    occurred = datetime(2025, 6, 15, 10, 5, 0, tzinfo=timezone.utc).isoformat()

    response = await client.post(
        "/api/v1/interactions/batch",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "events": [
                {
                    "perk_id": str(perk.id),
                    "type": "view",
                    "occurred_at": occurred,
                },
                {
                    "perk_id": str(uuid.uuid4()),
                    "type": "click",
                },
            ]
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["accepted"] == 1
    assert data["rejected"] == 1

    rows = await db_session.scalars(
        select(PerkInteraction).where(PerkInteraction.employee_id == employee.id)
    )
    assert len(list(rows.all())) == 1
