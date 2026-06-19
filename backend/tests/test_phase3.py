"""Phase 3 integration tests — cancellations, approvals, payments, notifications, packages."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password
from app.database import get_db
from app.main import create_app
from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import (
    NotificationType,
    PaymentStatus,
    PerkCategory,
    ProviderStatus,
    SelectionStatus,
    UserRole,
)
from app.models.notification import Notification
from app.models.package import Package, PackageItem
from app.models.payment import Payment
from app.models.perk import Perk
from app.models.provider import ProviderProfile
from app.models.selection import PerkSelection
from app.models.user import User
from app.services.payments import create_simulated_payment
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


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


async def _seed_org_stack(
    db_session: AsyncSession,
    *,
    allocated_cents: int = 20000,
    spent_cents: int = 0,
    pending_cents: int = 0,
) -> tuple[User, User, EmployeeProfile, EmployerOrganization, Perk, BudgetAllocation]:
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
        organization_name="Phase3 Corp",
        invite_code=f"P3-{uuid.uuid4().hex[:4].upper()}",
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
        first_name="Eli",
        last_name="Worker",
        department="Engineering",
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

    return employer_user, employee_user, employee, employer, perk, allocation


async def _quick_add(client: AsyncClient, token: str, perk_id: uuid.UUID) -> str:
    response = await client.post(
        "/api/v1/selections/quick-add",
        headers={"Authorization": f"Bearer {token}"},
        json={"perk_id": str(perk_id)},
    )
    assert response.status_code == 200
    return response.json()["data"]["selection_id"]


@pytest.mark.asyncio
async def test_cancel_pending_selection(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, _, _, perk, allocation = await _seed_org_stack(db_session)
    token = await _login(client, employee_user.email)
    selection_id = await _quick_add(client, token, perk.id)

    response = await client.delete(
        f"/api/v1/selections/{selection_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    refreshed = await db_session.scalar(
        select(PerkSelection).where(PerkSelection.id == uuid.UUID(selection_id))
    )
    assert refreshed is not None
    assert refreshed.status == SelectionStatus.cancelled

    await db_session.refresh(allocation)
    assert allocation.pending_cents == 0

    redis = await get_redis_client()
    from app.services.budget import budget_cache_key, ensure_budget_cached

    await ensure_budget_cached(redis, allocation)
    key = budget_cache_key(
        allocation.employer_id,
        allocation.employee_id,
        period_year=allocation.period_year,
        period_month=allocation.period_month,
    )
    assert int(await redis.get(key)) == allocation.allocated_cents


@pytest.mark.asyncio
async def test_cancel_non_pending_fails(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, _, _, perk, _ = await _seed_org_stack(db_session)
    employee_token = await _login(client, employee_user.email)
    selection_id = await _quick_add(client, employee_token, perk.id)

    employer_token = await _login(client, employer_user.email)
    await client.post(
        f"/api/v1/employer/approvals/{selection_id}/approve",
        headers={"Authorization": f"Bearer {employer_token}"},
    )

    response = await client.delete(
        f"/api/v1/selections/{selection_id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SELECTION_NOT_CANCELLABLE"


@pytest.mark.asyncio
async def test_employer_approvals_queue_org_scoped(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, _, employer, perk, _ = await _seed_org_stack(db_session)
    employee_token = await _login(client, employee_user.email)
    await _quick_add(client, employee_token, perk.id)

    other_employer_user = User(
        email=f"other-employer-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(other_employer_user)
    await db_session.flush()
    db_session.add(
        EmployerOrganization(
            user_id=other_employer_user.id,
            organization_name="Other Corp",
            invite_code=f"OTH-{uuid.uuid4().hex[:4].upper()}",
            contact_name="HR",
        )
    )
    await db_session.flush()

    employer_token = await _login(client, employer_user.email)
    response = await client.get(
        "/api/v1/employer/approvals",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 1
    assert rows[0]["employee"]["name"] == "Eli Worker"
    assert "provider_cost_cents" not in str(rows)

    other_token = await _login(client, other_employer_user.email)
    other_response = await client.get(
        "/api/v1/employer/approvals",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_response.status_code == 200
    assert other_response.json()["data"] == []


@pytest.mark.asyncio
async def test_approve_and_reject_update_budget(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, _, _, perk, allocation = await _seed_org_stack(db_session)
    employee_token = await _login(client, employee_user.email)
    selection_id = await _quick_add(client, employee_token, perk.id)
    employer_token = await _login(client, employer_user.email)

    reject_response = await client.post(
        f"/api/v1/employer/approvals/{selection_id}/reject",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"reason": "Not aligned with policy"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["status"] == "rejected"

    await db_session.refresh(allocation)
    assert allocation.pending_cents == 0
    assert allocation.spent_cents == 0

    selection_id_2 = await _quick_add(client, employee_token, perk.id)
    approve_response = await client.post(
        f"/api/v1/employer/approvals/{selection_id_2}/approve",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["data"]["status"] == "approved"

    await db_session.refresh(allocation)
    assert allocation.pending_cents == 0
    assert allocation.spent_cents == perk.employee_price_cents

    notif_count = await db_session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == employee_user.id,
            Notification.type.in_(
                [NotificationType.selection_rejected, NotificationType.selection_approved]
            ),
        )
    )
    assert notif_count == 2


@pytest.mark.asyncio
async def test_self_approval_forbidden(client: AsyncClient, db_session: AsyncSession):
    dual_user = User(
        email=f"dual-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(dual_user)
    await db_session.flush()

    employer = EmployerOrganization(
        user_id=dual_user.id,
        organization_name="Dual Role Corp",
        invite_code=f"DUAL-{uuid.uuid4().hex[:4].upper()}",
        contact_name="HR",
        default_currency_code="ALL",
    )
    db_session.add(employer)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=dual_user.id,
        employer_id=employer.id,
        first_name="Dual",
        last_name="User",
        onboarding_completed=True,
    )
    db_session.add(employee)
    await db_session.flush()

    provider_user = User(
        email=f"prov-dual-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.provider,
        is_verified=True,
    )
    db_session.add(provider_user)
    await db_session.flush()
    provider = ProviderProfile(user_id=provider_user.id, company_name="DualCo", status=ProviderStatus.active)
    db_session.add(provider)
    await db_session.flush()

    perk = Perk(
        provider_id=provider.id,
        name="Dual Perk",
        slug=f"dual-{uuid.uuid4().hex[:8]}",
        description="Perk",
        category=PerkCategory.wellness,
        employee_price_cents=4500,
        provider_cost_cents=3500,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(perk)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    allocation = BudgetAllocation(
        employer_id=employer.id,
        employee_id=employee.id,
        period_year=now.year,
        period_month=now.month,
        allocated_cents=20000,
        pending_cents=4500,
        currency_code="ALL",
    )
    db_session.add(allocation)
    await db_session.flush()

    selection = PerkSelection(
        employee_id=employee.id,
        perk_id=perk.id,
        employer_id=employer.id,
        budget_allocation_id=allocation.id,
        status=SelectionStatus.pending_approval,
        price_cents_snapshot=4500,
        currency_code="ALL",
    )
    db_session.add(selection)
    await db_session.flush()

    token = await _login(client, dual_user.email)
    response = await client.post(
        f"/api/v1/employer/approvals/{selection.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SELF_APPROVAL_FORBIDDEN"


@pytest.mark.asyncio
async def test_bulk_approve(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, _, _, perk, allocation = await _seed_org_stack(db_session)
    employee_token = await _login(client, employee_user.email)

    provider_user = User(
        email=f"provider2-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.provider,
        is_verified=True,
    )
    db_session.add(provider_user)
    await db_session.flush()
    provider2 = ProviderProfile(user_id=provider_user.id, company_name="Fit2", status=ProviderStatus.active)
    db_session.add(provider2)
    await db_session.flush()
    perk2 = Perk(
        provider_id=provider2.id,
        name="Gym",
        slug=f"gym-{uuid.uuid4().hex[:8]}",
        description="Gym",
        category=PerkCategory.fitness,
        employee_price_cents=3000,
        provider_cost_cents=2000,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(perk2)
    await db_session.flush()

    sel1 = await _quick_add(client, employee_token, perk.id)
    sel2 = await _quick_add(client, employee_token, perk2.id)

    employer_token = await _login(client, employer_user.email)
    response = await client.post(
        "/api/v1/employer/approvals/bulk-approve",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"selection_ids": [sel1, sel2]},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["approved"] == 2
    assert data["failed"] == 0

    await db_session.refresh(allocation)
    assert allocation.spent_cents == perk.employee_price_cents + perk2.employee_price_cents


@pytest.mark.asyncio
async def test_package_batch_approve(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, employee, employer, _, allocation = await _seed_org_stack(db_session)

    provider_a_user = User(
        email=f"pa-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.provider,
        is_verified=True,
    )
    provider_b_user = User(
        email=f"pb-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.provider,
        is_verified=True,
    )
    db_session.add_all([provider_a_user, provider_b_user])
    await db_session.flush()

    provider_a = ProviderProfile(user_id=provider_a_user.id, company_name="GymCo", status=ProviderStatus.active)
    provider_b = ProviderProfile(user_id=provider_b_user.id, company_name="MealCo", status=ProviderStatus.active)
    db_session.add_all([provider_a, provider_b])
    await db_session.flush()

    perk_a = Perk(
        provider_id=provider_a.id,
        name="Gym",
        slug=f"gym-{uuid.uuid4().hex[:8]}",
        description="Gym",
        category=PerkCategory.fitness,
        employee_price_cents=3000,
        provider_cost_cents=2500,
        currency_code="ALL",
        is_active=True,
    )
    perk_b = Perk(
        provider_id=provider_b.id,
        name="Meals",
        slug=f"meal-{uuid.uuid4().hex[:8]}",
        description="Meals",
        category=PerkCategory.food,
        employee_price_cents=2000,
        provider_cost_cents=1500,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add_all([perk_a, perk_b])
    await db_session.flush()

    package = Package(
        name="Wellness Starter",
        description="Bundle",
        category="wellness_bundle",
        is_curated=True,
        total_price_cents=5000,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(package)
    await db_session.flush()
    db_session.add_all(
        [
            PackageItem(package_id=package.id, perk_id=perk_a.id, quantity=1),
            PackageItem(package_id=package.id, perk_id=perk_b.id, quantity=1),
        ]
    )
    await db_session.flush()

    employee_token = await _login(client, employee_user.email)
    pkg_response = await client.post(
        f"/api/v1/selections/package/{package.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert pkg_response.status_code == 200
    selection_ids = pkg_response.json()["data"]["selection_ids"]
    assert len(selection_ids) == 2

    employer_token = await _login(client, employer_user.email)
    approve_response = await client.post(
        f"/api/v1/employer/approvals/{selection_ids[0]}/approve",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["data"]["approved_count"] == 2

    statuses = await db_session.scalars(
        select(PerkSelection.status).where(
            PerkSelection.id.in_([uuid.UUID(sid) for sid in selection_ids])
        )
    )
    assert all(status == SelectionStatus.approved for status in statuses.all())

    await db_session.refresh(allocation)
    assert allocation.spent_cents == 5000


@pytest.mark.asyncio
async def test_list_packages_and_select(client: AsyncClient, db_session: AsyncSession):
    _, employee_user, _, _, _, _ = await _seed_org_stack(db_session)

    provider_user = User(
        email=f"pkg-provider-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.provider,
        is_verified=True,
    )
    db_session.add(provider_user)
    await db_session.flush()
    provider = ProviderProfile(user_id=provider_user.id, company_name="PkgCo", status=ProviderStatus.active)
    db_session.add(provider)
    await db_session.flush()

    perk = Perk(
        provider_id=provider.id,
        name="Spa Day",
        slug=f"spa-{uuid.uuid4().hex[:8]}",
        description="Spa",
        category=PerkCategory.wellness,
        employee_price_cents=4000,
        provider_cost_cents=3000,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(perk)
    await db_session.flush()

    package = Package(
        name="Relax Pack",
        description="Spa bundle",
        is_curated=True,
        total_price_cents=4000,
        currency_code="ALL",
        is_active=True,
    )
    db_session.add(package)
    await db_session.flush()
    db_session.add(PackageItem(package_id=package.id, perk_id=perk.id, quantity=1))
    await db_session.flush()

    token = await _login(client, employee_user.email)
    list_response = await client.get(
        "/api/v1/packages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    packages = list_response.json()["data"]
    assert len(packages) >= 1
    assert "provider_cost_cents" not in str(packages)


@pytest.mark.asyncio
async def test_notifications_list_and_read(client: AsyncClient, db_session: AsyncSession):
    employer_user, employee_user, _, _, perk, _ = await _seed_org_stack(db_session)
    employee_token = await _login(client, employee_user.email)
    selection_id = await _quick_add(client, employee_token, perk.id)

    employer_token = await _login(client, employer_user.email)
    await client.post(
        f"/api/v1/employer/approvals/{selection_id}/approve",
        headers={"Authorization": f"Bearer {employer_token}"},
    )

    list_response = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert list_response.status_code == 200
    rows = list_response.json()["data"]
    assert len(rows) >= 1
    assert rows[0]["type"] == NotificationType.selection_approved.value

    notif_id = rows[0]["id"]
    read_response = await client.post(
        f"/api/v1/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["data"]["is_read"] is True

    read_all_response = await client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert read_all_response.status_code == 200


@pytest.mark.asyncio
async def test_simulated_payment_creates_completed_rows(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    employer_user, employee_user, _, _, perk, _ = await _seed_org_stack(db_session)
    employee_token = await _login(client, employee_user.email)
    selection_id = await _quick_add(client, employee_token, perk.id)
    employer_token = await _login(client, employer_user.email)
    await client.post(
        f"/api/v1/employer/approvals/{selection_id}/approve",
        headers={"Authorization": f"Bearer {employer_token}"},
    )

    class _SessionCtx:
        def __init__(self, session: AsyncSession) -> None:
            self._session = session

        async def __aenter__(self) -> AsyncSession:
            return self._session

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "app.services.payments.AsyncSessionLocal",
        lambda: _SessionCtx(db_session),
    )

    await create_simulated_payment(uuid.UUID(selection_id))

    payment = await db_session.scalar(
        select(Payment).where(Payment.perk_selection_id == uuid.UUID(selection_id))
    )
    assert payment is not None
    assert payment.status == PaymentStatus.completed

    notif = await db_session.scalar(
        select(Notification).where(
            Notification.user_id == employee_user.id,
            Notification.type == NotificationType.system,
        )
    )
    assert notif is not None
    assert "Payment confirmed" in notif.title
