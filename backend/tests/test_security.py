"""Security layer tests — RBAC, field exclusion, revocation, rate limits, injection."""

from __future__ import annotations

import uuid

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
from app.models.enums import PerkCategory, ProviderStatus, UserRole
from app.models.perk import Perk
from app.models.provider import ProviderProfile
from app.models.user import User
from app.utils.redis import reset_redis_for_tests


@pytest.fixture(autouse=True)
def memory_redis(monkeypatch):
    """Force in-memory Redis for deterministic security tests."""

    monkeypatch.setenv("REDIS_USE_MEMORY", "true")


@pytest.fixture(autouse=True)
async def reset_rate_limits():
    """Reset in-memory Redis counters between security tests."""

    await reset_redis_for_tests()
    yield
    await reset_redis_for_tests()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Async HTTP client with DB session override."""

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def _create_verified_user(
    db_session: AsyncSession,
    *,
    email: str,
    password: str,
    role: UserRole,
    employer: EmployerOrganization | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    if role == UserRole.employer:
        db_session.add(
            EmployerOrganization(
                user_id=user.id,
                organization_name="Acme Corp",
                invite_code=f"ACME-{uuid.uuid4().hex[:4].upper()}",
                contact_name="HR",
            )
        )
    elif role == UserRole.provider:
        db_session.add(
            ProviderProfile(
                user_id=user.id,
                company_name="FlowFit",
                status=ProviderStatus.active,
            )
        )
    elif role == UserRole.employee and employer is not None:
        db_session.add(
            EmployeeProfile(
                user_id=user.id,
                employer_id=employer.id,
                first_name="John",
                last_name="Doe",
            )
        )

    await db_session.flush()
    return user


async def _employer_for_user(db_session: AsyncSession, user: User) -> EmployerOrganization:
    employer = await db_session.scalar(
        select(EmployerOrganization).where(EmployerOrganization.user_id == user.id)
    )
    assert employer is not None
    return employer


async def _provider_for_user(db_session: AsyncSession, user: User) -> ProviderProfile:
    provider = await db_session.scalar(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )
    assert provider is not None
    return provider


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["data"]


@pytest.mark.asyncio
async def test_rbac_employee_cannot_access_admin_stats(client: AsyncClient, db_session: AsyncSession):
    employer_user = await _create_verified_user(
        db_session,
        email=f"employer-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.employer,
    )
    employer = await _employer_for_user(db_session, employer_user)
    employee = await _create_verified_user(
        db_session,
        email=f"employee-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.employee,
        employer=employer,
    )

    tokens = await _login(client, employee.email, "Secret123")
    response = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_rbac_admin_can_access_admin_stats(client: AsyncClient, db_session: AsyncSession):
    user = await _create_verified_user(
        db_session,
        email=f"admin-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.admin,
    )
    tokens = await _login(client, user.email, "Secret123")
    response = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "users_total" in data
    assert "providers_pending_review" in data
    assert "pending_providers" in data


@pytest.mark.asyncio
async def test_rbac_employer_cannot_access_employee_me(client: AsyncClient, db_session: AsyncSession):
    user = await _create_verified_user(
        db_session,
        email=f"employer-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.employer,
    )
    tokens = await _login(client, user.email, "Secret123")
    response = await client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_employee_perk_response_excludes_provider_cost_cents(
    client: AsyncClient,
    db_session: AsyncSession,
):
    employer_user = await _create_verified_user(
        db_session,
        email=f"employer-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.employer,
    )
    employer = await _employer_for_user(db_session, employer_user)
    provider_user = await _create_verified_user(
        db_session,
        email=f"provider-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.provider,
    )
    provider = await _provider_for_user(db_session, provider_user)
    employee = await _create_verified_user(
        db_session,
        email=f"employee-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.employee,
        employer=employer,
    )
    perk = Perk(
        provider_id=provider.id,
        name="Yoga Pass",
        slug=f"yoga-{uuid.uuid4().hex[:8]}",
        description="Monthly yoga",
        category=PerkCategory.wellness,
        employee_price_cents=4500,
        provider_cost_cents=3500,
    )
    db_session.add(perk)
    await db_session.flush()

    tokens = await _login(client, employee.email, "Secret123")
    response = await client.get(
        f"/api/v1/perks/{perk.id}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert "provider_cost_cents" not in payload
    assert payload["employee_price_cents"] == 4500


@pytest.mark.asyncio
async def test_provider_perk_response_includes_provider_cost_cents(
    client: AsyncClient,
    db_session: AsyncSession,
):
    provider_user = await _create_verified_user(
        db_session,
        email=f"provider-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.provider,
    )
    provider = await _provider_for_user(db_session, provider_user)
    perk = Perk(
        provider_id=provider.id,
        name="Gym Pass",
        slug=f"gym-{uuid.uuid4().hex[:8]}",
        description="Monthly gym",
        category=PerkCategory.fitness,
        employee_price_cents=3000,
        provider_cost_cents=2500,
    )
    db_session.add(perk)
    await db_session.flush()

    tokens = await _login(client, provider_user.email, "Secret123")
    response = await client.get(
        f"/api/v1/perks/{perk.id}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["provider_cost_cents"] == 2500


@pytest.mark.asyncio
async def test_logged_out_jti_is_rejected(client: AsyncClient, db_session: AsyncSession):
    user = await _create_verified_user(
        db_session,
        email=f"employer-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.employer,
    )
    login_data = await _login(client, user.email, "Secret123")
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 204

    protected = await client.get(
        "/api/v1/employer/organization",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert protected.status_code == 401
    assert protected.json()["error"]["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_sixth_login_within_minute_returns_429(client: AsyncClient, db_session: AsyncSession):
    user = await _create_verified_user(
        db_session,
        email=f"login-rate-{uuid.uuid4()}@test.example.com",
        password="Secret123",
        role=UserRole.employer,
    )

    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "Secret123"},
        )
        assert response.status_code == 200

    sixth = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Secret123"},
    )
    assert sixth.status_code == 429
    assert sixth.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in sixth.headers


@pytest.mark.asyncio
async def test_register_sql_injection_probe_returns_422(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "Secret123",
            "role": "employee",
            "employer_code": "'; DROP TABLE users; --",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_blocks_unverified_email(client: AsyncClient, db_session: AsyncSession):
    user = User(
        email=f"unverified-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        EmployerOrganization(
            user_id=user.id,
            organization_name="Pending Org",
            invite_code=f"PEND-{uuid.uuid4().hex[:4].upper()}",
            contact_name="HR",
        )
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Secret123"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
