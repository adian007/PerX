"""Relationship integrity test for multi-provider packages and payments."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import ForeignKey, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import PerkCategory, SelectionStatus, UserRole
from app.models.package import Package, PackageItem
from app.models.payment import Payment
from app.models.perk import Perk
from app.models.provider import ProviderProfile, ProviderRating
from app.models.selection import PerkSelection
from app.models.user import User


async def _create_user(session: AsyncSession, email: str, role: UserRole) -> User:
    user = User(email=email, hashed_password="hashed-test", role=role)
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_multi_provider_package_payment_chain_and_rating_uniqueness(
    db_session: AsyncSession,
) -> None:
    """Prove package→multi-provider chain, dual payments, and rating uniqueness."""

    employer_user = await _create_user(db_session, f"employer-{uuid.uuid4()}@test.example.com", UserRole.employer)
    employee_user = await _create_user(db_session, f"employee-{uuid.uuid4()}@test.example.com", UserRole.employee)
    provider_a_user = await _create_user(db_session, f"provider-a-{uuid.uuid4()}@test.example.com", UserRole.provider)
    provider_b_user = await _create_user(db_session, f"provider-b-{uuid.uuid4()}@test.example.com", UserRole.provider)

    employer = EmployerOrganization(
        user_id=employer_user.id,
        organization_name="Test Corp",
        invite_code=f"TEST-{uuid.uuid4().hex[:6].upper()}",
        contact_name="HR Lead",
        default_currency_code="ALL",
    )
    db_session.add(employer)
    await db_session.flush()

    employee = EmployeeProfile(
        user_id=employee_user.id,
        employer_id=employer.id,
        first_name="Ada",
        last_name="Lovelace",
    )
    db_session.add(employee)
    await db_session.flush()

    provider_a = ProviderProfile(user_id=provider_a_user.id, company_name="Gym Alpha")
    provider_b = ProviderProfile(user_id=provider_b_user.id, company_name="Meals Beta")
    db_session.add_all([provider_a, provider_b])
    await db_session.flush()

    perk_a = Perk(
        provider_id=provider_a.id,
        name="Gym Membership",
        slug=f"gym-{uuid.uuid4().hex[:8]}",
        description="Monthly gym access",
        category=PerkCategory.fitness,
        employee_price_cents=3000,
        provider_cost_cents=2500,
        currency_code="ALL",
    )
    perk_b = Perk(
        provider_id=provider_b.id,
        name="Meal Plan",
        slug=f"meals-{uuid.uuid4().hex[:8]}",
        description="Healthy meal subscription",
        category=PerkCategory.food,
        employee_price_cents=2000,
        provider_cost_cents=1500,
        currency_code="ALL",
    )
    db_session.add_all([perk_a, perk_b])
    await db_session.flush()

    allocation = BudgetAllocation(
        employer_id=employer.id,
        employee_id=employee.id,
        period_year=2026,
        period_month=6,
        allocated_cents=100_000,
        currency_code="ALL",
    )
    db_session.add(allocation)
    await db_session.flush()

    package = Package(
        name="Wellness Starter",
        description="Gym + meals bundle",
        category="wellness_bundle",
        is_curated=True,
        total_price_cents=5000,
        currency_code="ALL",
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

    chain_result = await db_session.execute(
        select(
            Package.name,
            ProviderProfile.company_name,
            Perk.name,
        )
        .join(PackageItem, PackageItem.package_id == Package.id)
        .join(Perk, Perk.id == PackageItem.perk_id)
        .join(ProviderProfile, ProviderProfile.id == Perk.provider_id)
        .where(Package.id == package.id)
        .order_by(ProviderProfile.company_name)
    )
    chain_rows = chain_result.all()
    assert len(chain_rows) == 2
    providers_in_chain = {row.company_name for row in chain_rows}
    assert providers_in_chain == {"Gym Alpha", "Meals Beta"}

    selection = PerkSelection(
        employee_id=employee.id,
        perk_id=perk_a.id,
        employer_id=employer.id,
        budget_allocation_id=allocation.id,
        package_id=package.id,
        status=SelectionStatus.approved,
        price_cents_snapshot=5000,
        currency_code="ALL",
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add(selection)
    await db_session.flush()

    db_session.add_all(
        [
            Payment(
                perk_selection_id=selection.id,
                provider_id=provider_a.id,
                employer_id=employer.id,
                amount_cents=3000,
                currency_code="ALL",
                status="completed",
                simulated=True,
                processed_at=datetime.now(timezone.utc),
            ),
            Payment(
                perk_selection_id=selection.id,
                provider_id=provider_b.id,
                employer_id=employer.id,
                amount_cents=2000,
                currency_code="ALL",
                status="completed",
                simulated=True,
                processed_at=datetime.now(timezone.utc),
            ),
        ]
    )
    await db_session.flush()

    payment_count = await db_session.scalar(
        select(func.count()).select_from(Payment).where(Payment.perk_selection_id == selection.id)
    )
    assert payment_count == 2

    db_session.add(
        ProviderRating(
            employee_id=employee.id,
            provider_id=provider_a.id,
            perk_id=perk_a.id,
            selection_id=selection.id,
            rating=5,
            comment="Great bundle",
        )
    )
    await db_session.flush()

    db_session.add(
        ProviderRating(
            employee_id=employee.id,
            provider_id=provider_b.id,
            perk_id=perk_b.id,
            selection_id=selection.id,
            rating=4,
            comment="Duplicate should fail",
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()
