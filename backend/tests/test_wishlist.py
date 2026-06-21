"""Wishlist CRUD API tests."""

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
from app.models.employee import EmployeeProfile, EmployeeWishlist
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


async def _seed_employee_with_perk(
    db_session: AsyncSession,
    *,
    perk_active: bool = True,
) -> tuple[User, Perk]:
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
        organization_name="Wish Corp",
        invite_code=f"WISH-{uuid.uuid4().hex[:4].upper()}",
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
        first_name="Wish",
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
        company_name="WishFit",
        status=ProviderStatus.active,
    )
    db_session.add(provider)
    await db_session.flush()

    perk = Perk(
        provider_id=provider.id,
        name="Spa Day",
        slug=f"spa-{uuid.uuid4().hex[:8]}",
        description="Relaxation package",
        category=PerkCategory.wellness,
        employee_price_cents=3000,
        provider_cost_cents=2000,
        currency_code="ALL",
        is_active=perk_active,
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
async def test_get_wishlist_empty(client: AsyncClient, db_session: AsyncSession):
    user, _ = await _seed_employee_with_perk(db_session)
    token = await _login(client, user.email)

    response = await client.get(
        "/api/v1/me/wishlist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_add_and_list_wishlist(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_with_perk(db_session)
    token = await _login(client, user.email)

    add_response = await client.post(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert add_response.status_code == 201
    assert add_response.json()["data"]["added"] is True
    assert add_response.json()["data"]["perk_id"] == str(perk.id)

    list_response = await client.get(
        "/api/v1/me/wishlist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    items = list_response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == str(perk.id)
    assert "provider_cost_cents" not in items[0]


@pytest.mark.asyncio
async def test_add_wishlist_logs_interaction(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_with_perk(db_session)
    token = await _login(client, user.email)

    await client.post(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    rows = await db_session.scalars(
        select(PerkInteraction).where(
            PerkInteraction.perk_id == perk.id,
            PerkInteraction.interaction_type == InteractionType.add_to_wishlist,
        )
    )
    assert len(list(rows.all())) == 1


@pytest.mark.asyncio
async def test_add_wishlist_duplicate(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_with_perk(db_session)
    token = await _login(client, user.email)

    await client.post(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.post(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_IN_WISHLIST"


@pytest.mark.asyncio
async def test_add_inactive_perk(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_with_perk(db_session, perk_active=False)
    token = await _login(client, user.email)

    response = await client.post(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PERK_INACTIVE"


@pytest.mark.asyncio
async def test_remove_from_wishlist(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_with_perk(db_session)
    employee = await db_session.scalar(
        select(EmployeeProfile).where(EmployeeProfile.user_id == user.id)
    )
    assert employee is not None
    token = await _login(client, user.email)

    await client.post(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    delete_response = await client.delete(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    rows = await db_session.scalars(
        select(EmployeeWishlist).where(EmployeeWishlist.employee_id == employee.id)
    )
    assert len(list(rows.all())) == 0

    interaction_rows = await db_session.scalars(
        select(PerkInteraction).where(
            PerkInteraction.employee_id == employee.id,
            PerkInteraction.interaction_type == InteractionType.remove_from_wishlist,
        )
    )
    assert len(list(interaction_rows.all())) == 1


@pytest.mark.asyncio
async def test_remove_missing_wishlist_item(client: AsyncClient, db_session: AsyncSession):
    user, perk = await _seed_employee_with_perk(db_session)
    token = await _login(client, user.email)

    response = await client.delete(
        f"/api/v1/me/wishlist/{perk.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
