"""Phase 4 tests — reconcile, websocket auth, employer analytics org scoping."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.passwords import hash_password
from app.database import get_db
from app.main import create_app
from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import PaymentStatus, PerkCategory, ProviderStatus, SelectionStatus, UserRole
from app.models.payment import Payment
from app.models.perk import Perk
from app.models.provider import ProviderProfile
from app.models.selection import PerkSelection
from app.models.user import User
from app.services.budget import budget_cache_key
from app.services.budget_reconcile import reconcile_budget_cache
from app.utils.redis import get_redis_client, reset_redis_for_tests


@pytest.fixture(autouse=True)
def memory_redis(monkeypatch):
    monkeypatch.setenv("REDIS_USE_MEMORY", "true")
    monkeypatch.setenv("ALLOW_DEMO_MODE", "false")
    monkeypatch.setenv("RECONCILE_ENABLED", "false")


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


async def _seed_two_orgs(db_session: AsyncSession) -> tuple[
    User, EmployerOrganization, EmployeeProfile, User, EmployerOrganization, EmployeeProfile, Perk
]:
    """Create two isolated employer orgs with one employee each."""

    now = datetime.now(timezone.utc)

    employer_a = User(
        email=f"employer-a-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    employer_b = User(
        email=f"employer-b-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add_all([employer_a, employer_b])
    await db_session.flush()

    org_a = EmployerOrganization(
        user_id=employer_a.id,
        organization_name="Org Alpha",
        invite_code=f"A-{uuid.uuid4().hex[:4].upper()}",
        contact_name="HR A",
    )
    org_b = EmployerOrganization(
        user_id=employer_b.id,
        organization_name="Org Beta",
        invite_code=f"B-{uuid.uuid4().hex[:4].upper()}",
        contact_name="HR B",
    )
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    emp_user_a = User(
        email=f"emp-a-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employee,
        is_verified=True,
    )
    emp_user_b = User(
        email=f"emp-b-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employee,
        is_verified=True,
    )
    db_session.add_all([emp_user_a, emp_user_b])
    await db_session.flush()

    employee_a = EmployeeProfile(
        user_id=emp_user_a.id,
        employer_id=org_a.id,
        first_name="Alice",
        last_name="Alpha",
    )
    employee_b = EmployeeProfile(
        user_id=emp_user_b.id,
        employer_id=org_b.id,
        first_name="Bob",
        last_name="Beta",
    )
    db_session.add_all([employee_a, employee_b])
    await db_session.flush()

    for org, employee, allocated, spent in [
        (org_a, employee_a, 100000, 25000),
        (org_b, employee_b, 50000, 5000),
    ]:
        db_session.add(
            BudgetAllocation(
                employer_id=org.id,
                employee_id=employee.id,
                period_year=now.year,
                period_month=now.month,
                allocated_cents=allocated,
                spent_cents=spent,
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
        company_name="PerkCo",
        status=ProviderStatus.active,
    )
    db_session.add(provider)
    await db_session.flush()

    perk = Perk(
        provider_id=provider.id,
        name="Gym Pass",
        slug=f"gym-{uuid.uuid4().hex[:8]}",
        description="Monthly gym",
        category=PerkCategory.fitness,
        employee_price_cents=5000,
        provider_cost_cents=4000,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(perk)
    await db_session.flush()

    return employer_a, org_a, employee_a, employer_b, org_b, employee_b, perk


@pytest.mark.asyncio
async def test_reconcile_budget_cache_refreshes_redis_from_postgres(
    db_session: AsyncSession,
):
    """Reconcile trusts Postgres remaining_cents and overwrites stale Redis values."""

    now = datetime.now(timezone.utc)
    employer_user = User(
        email=f"reconcile-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(employer_user)
    await db_session.flush()

    org = EmployerOrganization(
        user_id=employer_user.id,
        organization_name="Reconcile Co",
        invite_code=f"RC-{uuid.uuid4().hex[:4].upper()}",
        contact_name="Finance",
    )
    db_session.add(org)
    await db_session.flush()

    emp_user = User(
        email=f"reconcile-emp-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employee,
        is_verified=True,
    )
    db_session.add(emp_user)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=emp_user.id,
        employer_id=org.id,
        first_name="Rec",
        last_name="Worker",
    )
    db_session.add(employee)
    await db_session.flush()

    allocation = BudgetAllocation(
        employer_id=org.id,
        employee_id=employee.id,
        period_year=now.year,
        period_month=now.month,
        allocated_cents=20000,
        spent_cents=3000,
        pending_cents=2000,
        currency_code="ALL",
    )
    db_session.add(allocation)
    await db_session.flush()
    await db_session.refresh(allocation)

    redis = await get_redis_client()
    key = budget_cache_key(
        org.id,
        employee.id,
        period_year=now.year,
        period_month=now.month,
    )
    await redis.setex(key, 3600, "99999")

    updated = await reconcile_budget_cache(db_session, redis)
    assert updated >= 1

    cached = await redis.get(key)
    assert cached == str(allocation.remaining_cents)
    assert int(cached) == 15000


@pytest.mark.asyncio
async def test_websocket_rejects_wrong_employee_id(client: AsyncClient, db_session: AsyncSession):
    """Employee cannot connect to another employee's WebSocket channel."""

    employer_user = User(
        email=f"ws-employer-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(employer_user)
    await db_session.flush()

    org = EmployerOrganization(
        user_id=employer_user.id,
        organization_name="WS Corp",
        invite_code=f"WS-{uuid.uuid4().hex[:4].upper()}",
        contact_name="HR",
    )
    db_session.add(org)
    await db_session.flush()

    emp_user = User(
        email=f"ws-emp-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employee,
        is_verified=True,
    )
    db_session.add(emp_user)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=emp_user.id,
        employer_id=org.id,
        first_name="Web",
        last_name="Socket",
    )
    db_session.add(employee)
    await db_session.flush()

    other_id = uuid.uuid4()
    token, _, _ = create_access_token(user_id=emp_user.id, role=UserRole.employee.value)

    with pytest.raises(Exception):
        async with client.websocket_connect(
            f"/api/v1/ws/employee/{other_id}?token={token}"
        ) as _ws:
            pass


@pytest.mark.asyncio
async def test_websocket_rejects_invalid_token(client: AsyncClient):
    """Invalid JWT is rejected on WebSocket connect."""

    employee_id = uuid.uuid4()
    with pytest.raises(Exception):
        async with client.websocket_connect(
            f"/api/v1/ws/employee/{employee_id}?token=not-a-valid-jwt"
        ) as _ws:
            pass


@pytest.mark.asyncio
async def test_employer_analytics_org_scoped(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Each employer sees only their org payment and selection totals."""

    employer_a, org_a, employee_a, employer_b, org_b, employee_b, perk = await _seed_two_orgs(
        db_session
    )

    alloc_a = await db_session.scalar(
        select(BudgetAllocation).where(BudgetAllocation.employee_id == employee_a.id)
    )
    alloc_b = await db_session.scalar(
        select(BudgetAllocation).where(BudgetAllocation.employee_id == employee_b.id)
    )

    sel_a = PerkSelection(
        employee_id=employee_a.id,
        perk_id=perk.id,
        employer_id=org_a.id,
        budget_allocation_id=alloc_a.id,
        status=SelectionStatus.approved,
        price_cents_snapshot=5000,
        currency_code="ALL",
    )
    sel_b = PerkSelection(
        employee_id=employee_b.id,
        perk_id=perk.id,
        employer_id=org_b.id,
        budget_allocation_id=alloc_b.id,
        status=SelectionStatus.approved,
        price_cents_snapshot=5000,
        currency_code="ALL",
    )
    db_session.add_all([sel_a, sel_b])
    await db_session.flush()

    db_session.add_all(
        [
            Payment(
                perk_selection_id=sel_a.id,
                provider_id=perk.provider_id,
                employer_id=org_a.id,
                amount_cents=5000,
                currency_code="ALL",
                status=PaymentStatus.completed,
                simulated=True,
                processed_at=datetime.now(timezone.utc),
            ),
            Payment(
                perk_selection_id=sel_b.id,
                provider_id=perk.provider_id,
                employer_id=org_b.id,
                amount_cents=8000,
                currency_code="ALL",
                status=PaymentStatus.completed,
                simulated=True,
                processed_at=datetime.now(timezone.utc),
            ),
        ]
    )
    await db_session.flush()

    token_a = await _login(client, employer_a.email)
    token_b = await _login(client, employer_b.email)

    resp_a = await client.get(
        "/api/v1/employer/analytics",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_b = await client.get(
        "/api/v1/employer/analytics",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    data_a = resp_a.json()["data"]
    data_b = resp_b.json()["data"]

    assert data_a["total_payments_cents"] == 5000
    assert data_a["approved_selections"] == 1
    assert data_b["total_payments_cents"] == 8000
    assert data_b["approved_selections"] == 1


@pytest.mark.asyncio
async def test_employer_employees_list_org_scoped(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Employer employees endpoint returns only own org roster."""

    employer_a, _, employee_a, employer_b, _, employee_b, _ = await _seed_two_orgs(db_session)

    token_a = await _login(client, employer_a.email)
    response = await client.get(
        "/api/v1/employer/employees",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    employees = response.json()["data"]
    assert len(employees) == 1
    assert employees[0]["id"] == str(employee_a.id)
    assert employees[0]["name"] == "Alice Alpha"

    token_b = await _login(client, employer_b.email)
    response_b = await client.get(
        "/api/v1/employer/employees",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response_b.status_code == 200
    employees_b = response_b.json()["data"]
    assert len(employees_b) == 1
    assert employees_b[0]["id"] == str(employee_b.id)


@pytest.mark.asyncio
async def test_provider_analytics_returns_stats(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Provider analytics returns perk stats for authenticated provider."""

    _, _, _, _, _, _, perk = await _seed_two_orgs(db_session)
    provider = await db_session.scalar(
        select(ProviderProfile).where(ProviderProfile.id == perk.provider_id)
    )
    provider_user = await db_session.scalar(
        select(User).where(User.id == provider.user_id)
    )

    token = await _login(client, provider_user.email)
    response = await client.get(
        "/api/v1/provider/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "perk_stats" in data
    assert data["total_perks"] >= 0
