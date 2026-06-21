"""Ask PerX chat API tests."""

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
from app.models.enums import UserRole
from app.models.user import User
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


async def _seed_employee(db_session: AsyncSession) -> User:
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
        organization_name="Chat Corp",
        invite_code=f"CHAT-{uuid.uuid4().hex[:4].upper()}",
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
        first_name="Chat",
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
    return employee_user


async def _seed_employer(db_session: AsyncSession) -> User:
    user = User(
        email=f"employer-only-{uuid.uuid4()}@test.example.com",
        hashed_password=hash_password("Secret123"),
        role=UserRole.employer,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        EmployerOrganization(
            user_id=user.id,
            organization_name="Employer Only",
            invite_code=f"EMP-{uuid.uuid4().hex[:4].upper()}",
            contact_name="HR",
        )
    )
    await db_session.flush()
    return user


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secret123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_chat_employee_only(client: AsyncClient, db_session: AsyncSession):
    employer = await _seed_employer(db_session)
    token = await _login(client, employer.email)

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "What perks do I have?"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_chat_budget_shortcut(client: AsyncClient, db_session: AsyncSession):
    employee = await _seed_employee(db_session)
    token = await _login(client, employee.email)

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "How much budget do I have left?"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["source"] == "api"
    assert body["model"] == "shortcut"
    assert "remaining" in body["reply"].lower()
    assert len(body["actions"]) >= 1
    assert body["actions"][0]["type"] == "link"


@pytest.mark.asyncio
async def test_chat_ollama_fallback_when_force_fail(client: AsyncClient, db_session: AsyncSession):
    employee = await _seed_employee(db_session)
    token = await _login(client, employee.email)

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Tell me about wellness perks in general"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["source"] == "fallback"
    assert body["reply"]
    assert "Chat" in body["reply"]
    assert body["actions"] == []


@pytest.mark.asyncio
async def test_chat_accepts_history(client: AsyncClient, db_session: AsyncSession):
    employee = await _seed_employee(db_session)
    token = await _login(client, employee.email)

    response = await client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "And what about food?",
            "history": [
                {"role": "user", "content": "What categories fit me?"},
                {"role": "assistant", "content": "Wellness and food look strong."},
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["reply"]
