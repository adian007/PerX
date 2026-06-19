"""Seed development data including ADR-007 curated multi-provider packages.

Run from backend/:
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import PaymentStatus, PerkCategory, ProviderStatus, SelectionStatus, UserRole
from app.models.package import Package, PackageItem
from app.models.payment import Payment
from app.models.perk import Perk
from app.models.provider import ProviderProfile
from app.models.selection import PerkSelection
from app.models.user import User

SEED_EMPLOYER_EMAIL = "hr@demo.perx.local"


async def seed() -> None:
    """Insert demo employers, employees, perks, packages, and sample payments."""

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(User.id).where(User.email == SEED_EMPLOYER_EMAIL)
        )
        if existing is not None:
            print("Seed data already present — skipping.")
            return

        employer_user = User(
            email=SEED_EMPLOYER_EMAIL,
            hashed_password="seed-not-for-login",
            role=UserRole.employer,
            locale="sq-AL",
        )
        employee_cold_user = User(
            email="john.cold@demo.perx.local",
            hashed_password="seed-not-for-login",
            role=UserRole.employee,
            locale="sq-AL",
        )
        employee_warm_user = User(
            email="mira.warm@demo.perx.local",
            hashed_password="seed-not-for-login",
            role=UserRole.employee,
            locale="sq-AL",
        )
        provider_a_user = User(
            email="flowfit@demo.perx.local",
            hashed_password="seed-not-for-login",
            role=UserRole.provider,
            locale="sq-AL",
        )
        provider_b_user = User(
            email="greenbite@demo.perx.local",
            hashed_password="seed-not-for-login",
            role=UserRole.provider,
            locale="sq-AL",
        )
        session.add_all(
            [
                employer_user,
                employee_cold_user,
                employee_warm_user,
                provider_a_user,
                provider_b_user,
            ]
        )
        await session.flush()

        employer = EmployerOrganization(
            user_id=employer_user.id,
            organization_name="Demo Corp Albania",
            invite_code="ACME-DEMO",
            contact_name="HR Team",
            address_country="AL",
            default_monthly_budget_cents=50000,
            default_currency_code="ALL",
        )
        session.add(employer)
        await session.flush()

        employee_cold = EmployeeProfile(
            user_id=employee_cold_user.id,
            employer_id=employer.id,
            first_name="John",
            last_name="Cold",
            interaction_count=3,
            recommender_mode="cold_start",
            onboarding_completed=True,
            lifestyle_tags=["cyclist", "remote_worker"],
            preferred_categories=[PerkCategory.fitness, PerkCategory.wellness],
            budget_sensitivity="medium",
            wellness_priority=8,
            family_situation="couple",
        )
        employee_warm = EmployeeProfile(
            user_id=employee_warm_user.id,
            employer_id=employer.id,
            first_name="Mira",
            last_name="Warm",
            interaction_count=12,
            recommender_mode="warm",
            onboarding_completed=True,
            lifestyle_tags=["gym_goer", "foodie"],
            preferred_categories=[PerkCategory.fitness, PerkCategory.food],
            budget_sensitivity="medium",
            wellness_priority=7,
            family_situation="single",
        )
        session.add_all([employee_cold, employee_warm])
        await session.flush()

        provider_a = ProviderProfile(
            user_id=provider_a_user.id,
            company_name="FlowFit Tirana",
            status=ProviderStatus.active,
            available_countries=["AL"],
        )
        provider_b = ProviderProfile(
            user_id=provider_b_user.id,
            company_name="GreenBite Albania",
            status=ProviderStatus.active,
            available_countries=["AL"],
        )
        session.add_all([provider_a, provider_b])
        await session.flush()

        perks = [
            Perk(
                provider_id=provider_a.id,
                name="Blloku Fitness Club",
                slug="premium-gym-demo",
                description="Nationwide gym access.",
                short_description="Gym access nationwide.",
                category=PerkCategory.fitness,
                employee_price_cents=3500,
                provider_cost_cents=2800,
                currency_code="ALL",
                quality_score=0.88,
                popularity_score=0.75,
            ),
            Perk(
                provider_id=provider_a.id,
                name="Tirana Yoga Studio",
                slug="yoga-pass-demo",
                description="Monthly yoga classes.",
                short_description="Yoga studio monthly pass.",
                category=PerkCategory.wellness,
                employee_price_cents=4500,
                provider_cost_cents=3600,
                currency_code="ALL",
                quality_score=0.9,
                popularity_score=0.7,
            ),
            Perk(
                provider_id=provider_b.id,
                name="Albanian Organic Meals",
                slug="meal-delivery-demo",
                description="Weekly healthy meal kits.",
                short_description="Healthy meal delivery credit.",
                category=PerkCategory.food,
                employee_price_cents=2000,
                provider_cost_cents=1600,
                currency_code="ALL",
                quality_score=0.82,
                popularity_score=0.65,
            ),
            Perk(
                provider_id=provider_b.id,
                name="Tirana Bike Share",
                slug="bike-share-demo",
                description="Annual bike share pass.",
                short_description="Bike share annual pass.",
                category=PerkCategory.transport,
                employee_price_cents=1500,
                provider_cost_cents=1200,
                currency_code="ALL",
                quality_score=0.8,
                popularity_score=0.6,
            ),
            Perk(
                provider_id=provider_a.id,
                name="Durrës Weekend Getaway",
                slug="rail-getaway-demo",
                description="Discounted rail packages.",
                short_description="Weekend rail travel package.",
                category=PerkCategory.travel,
                employee_price_cents=8000,
                provider_cost_cents=6400,
                currency_code="ALL",
                quality_score=0.9,
                popularity_score=0.9,
            ),
        ]
        session.add_all(perks)
        await session.flush()

        gym_perk, yoga_perk, meal_perk, bike_perk, travel_perk = perks

        packages = [
            Package(
                name="Wellness Starter",
                description="Gym + healthy meals from two providers.",
                category="wellness_bundle",
                is_curated=True,
                total_price_cents=5500,
                currency_code="ALL",
            ),
            Package(
                name="Active Commuter",
                description="Gym membership and bike share for daily wellness.",
                category="fitness_bundle",
                is_curated=True,
                total_price_cents=5000,
                currency_code="ALL",
            ),
            Package(
                name="Tirana Explorer",
                description="Travel getaway plus local transport perks.",
                category="travel_bundle",
                is_curated=True,
                total_price_cents=9500,
                currency_code="ALL",
            ),
        ]
        session.add_all(packages)
        await session.flush()

        wellness_pkg, commuter_pkg, explorer_pkg = packages

        session.add_all(
            [
                PackageItem(package_id=wellness_pkg.id, perk_id=gym_perk.id),
                PackageItem(package_id=wellness_pkg.id, perk_id=meal_perk.id),
                PackageItem(package_id=commuter_pkg.id, perk_id=gym_perk.id),
                PackageItem(package_id=commuter_pkg.id, perk_id=bike_perk.id),
                PackageItem(package_id=explorer_pkg.id, perk_id=travel_perk.id),
                PackageItem(package_id=explorer_pkg.id, perk_id=bike_perk.id),
            ]
        )

        now = datetime.now(timezone.utc)
        budget_cold = BudgetAllocation(
            employer_id=employer.id,
            employee_id=employee_cold.id,
            period_year=now.year,
            period_month=now.month,
            allocated_cents=50000,
            currency_code="ALL",
        )
        budget_warm = BudgetAllocation(
            employer_id=employer.id,
            employee_id=employee_warm.id,
            period_year=now.year,
            period_month=now.month,
            allocated_cents=50000,
            currency_code="ALL",
        )
        session.add_all([budget_cold, budget_warm])
        await session.flush()

        selection = PerkSelection(
            employee_id=employee_warm.id,
            perk_id=gym_perk.id,
            employer_id=employer.id,
            budget_allocation_id=budget_warm.id,
            package_id=wellness_pkg.id,
            status=SelectionStatus.approved,
            price_cents_snapshot=gym_perk.employee_price_cents,
            currency_code="ALL",
            approved_at=now,
        )
        session.add(selection)
        await session.flush()

        session.add_all(
            [
                Payment(
                    perk_selection_id=selection.id,
                    provider_id=provider_a.id,
                    employer_id=employer.id,
                    amount_cents=gym_perk.employee_price_cents,
                    currency_code="ALL",
                    status=PaymentStatus.completed.value,
                    simulated=True,
                    processed_at=now,
                ),
                Payment(
                    perk_selection_id=selection.id,
                    provider_id=provider_b.id,
                    employer_id=employer.id,
                    amount_cents=meal_perk.employee_price_cents,
                    currency_code="ALL",
                    status=PaymentStatus.completed.value,
                    simulated=True,
                    processed_at=now,
                ),
            ]
        )

        await session.commit()
        print("Seed complete: employer, 2 employees, 2 providers, 5 perks, 3 packages, 1 payment fan-out.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
