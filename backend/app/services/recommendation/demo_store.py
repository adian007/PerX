"""Small in-memory store for local demos and integration tests."""

from __future__ import annotations

from typing import Literal

from app.models.recommendation import EmployeeProfile, Perk, Provider

DemoProfile = Literal["new", "cold", "warm"]

DEMO_PROVIDER = Provider(
    id="provider-flowfit",
    company_name="FlowFit",
    logo_url="https://example.test/flowfit.png",
    avg_rating=4.7,
)

DEMO_NEW_EMPLOYEE = EmployeeProfile(
    id="employee-new",
    first_name="Alex",
    interaction_count=0,
    recommender_mode="cold_start",
    lifestyle_tags=[],
    preferred_categories=[],
    budget_sensitivity="medium",
    wellness_priority=5,
    family_situation="single",
)

DEMO_COLD_EMPLOYEE = EmployeeProfile(
    id="employee-demo",
    first_name="John",
    interaction_count=9,
    recommender_mode="cold_start",
    lifestyle_tags=["cyclist", "remote_worker"],
    preferred_categories=["fitness", "wellness", "food"],
    budget_sensitivity="medium",
    wellness_priority=8,
    family_situation="couple",
)

DEMO_WARM_EMPLOYEE = EmployeeProfile(
    id="employee-warm",
    first_name="Mira",
    interaction_count=12,
    recommender_mode="warm",
    lifestyle_tags=["gym_goer", "foodie"],
    preferred_categories=["fitness", "food"],
    budget_sensitivity="medium",
    wellness_priority=7,
    family_situation="single",
    affinity_vector={
        "fitness": 0.9,
        "travel": 0.15,
        "wellness": 0.8,
        "food": 0.55,
        "education": 0.3,
        "entertainment": 0.2,
        "transport": 0.6,
        "childcare": 0.1,
        "other": 0.1,
    },
)

# Backward-compatible alias
DEMO_EMPLOYEE = DEMO_COLD_EMPLOYEE

DEMO_PERKS = [
    Perk(
        id="perk-yoga",
        name="Urban Yoga Studio - Monthly Pass",
        category="wellness",
        short_description="Unlimited classes at partner studios.",
        image_url="https://example.test/yoga.png",
        employee_price_cents=4500,
        provider=DEMO_PROVIDER,
        tags=["yoga", "group_classes", "flexible"],
        quality_score=0.9,
        popularity_score=0.7,
        collaborative_score=0.72,
    ),
    Perk(
        id="perk-bike",
        name="Urban Bike Share Annual Pass",
        category="transport",
        short_description="City-wide bike sharing for your commute.",
        image_url="https://example.test/bike.png",
        employee_price_cents=1500,
        provider=DEMO_PROVIDER,
        tags=["cycling", "commute"],
        quality_score=0.8,
        popularity_score=0.6,
        collaborative_score=0.67,
    ),
    Perk(
        id="perk-course",
        name="Online Learning Credit",
        category="education",
        short_description="Use credits for professional learning.",
        image_url="https://example.test/course.png",
        employee_price_cents=2500,
        provider=DEMO_PROVIDER,
        tags=["learning", "remote"],
        quality_score=0.85,
        popularity_score=0.5,
        collaborative_score=0.58,
    ),
    Perk(
        id="perk-gym",
        name="Premium Gym Membership",
        category="fitness",
        short_description="Access to partner gyms nationwide.",
        image_url="https://example.test/gym.png",
        employee_price_cents=3500,
        provider=DEMO_PROVIDER,
        tags=["gym", "fitness", "classes"],
        quality_score=0.88,
        popularity_score=0.75,
        collaborative_score=0.81,
    ),
    Perk(
        id="perk-meal",
        name="Healthy Meal Delivery Credit",
        category="food",
        short_description="Weekly meal kits from local partners.",
        image_url="https://example.test/meal.png",
        employee_price_cents=2000,
        provider=DEMO_PROVIDER,
        tags=["food", "healthy", "delivery"],
        quality_score=0.82,
        popularity_score=0.65,
        collaborative_score=0.63,
    ),
    Perk(
        id="perk-premium-travel",
        name="Weekend Rail Getaway",
        category="travel",
        short_description="Discounted rail packages for weekend travel.",
        image_url="https://example.test/rail.png",
        employee_price_cents=15000,
        provider=DEMO_PROVIDER,
        tags=["travel", "rail"],
        quality_score=0.9,
        popularity_score=0.9,
        collaborative_score=0.8,
    ),
]

DEMO_UCB_COUNTS = {
    "perk-yoga": 4,
    "perk-bike": 2,
    "perk-course": 1,
    "perk-gym": 3,
    "perk-meal": 0,
}

# Mutable store for onboarding demo — stand-in for Postgres + Redis affinity cache
_onboarded_profiles: dict[str, EmployeeProfile] = {}
_current_demo_employee_id: str = DEMO_COLD_EMPLOYEE.id


def resolve_demo_profile(demo: DemoProfile = "cold", warm_demo: bool = False) -> DemoProfile:
    """Resolve demo profile, keeping backward compatibility with warm_demo."""

    if warm_demo:
        return "warm"
    return demo


def get_demo_employee(
    demo: DemoProfile = "cold",
    warm: bool = False,
    warm_demo: bool = False,
) -> EmployeeProfile:
    """Return an in-memory employee profile for the requested demo mode."""

    profile_key = resolve_demo_profile(demo=demo, warm_demo=warm_demo or warm)
    if profile_key == "new":
        onboarded = _onboarded_profiles.get(DEMO_NEW_EMPLOYEE.id)
        return onboarded if onboarded is not None else DEMO_NEW_EMPLOYEE
    if profile_key == "warm":
        return DEMO_WARM_EMPLOYEE
    return DEMO_COLD_EMPLOYEE


def get_current_demo_employee_id() -> str:
    """Return the employee id used for onboarding explanation polling."""

    return _current_demo_employee_id


def set_current_demo_employee_id(employee_id: str) -> None:
    """Set the active demo employee for explanation polling."""

    global _current_demo_employee_id
    _current_demo_employee_id = employee_id


def save_onboarded_profile(profile: EmployeeProfile) -> None:
    """Persist an onboarded profile in the demo store."""

    _onboarded_profiles[profile.id] = profile


def get_demo_perks() -> list[Perk]:
    """Return in-memory active perks."""

    return DEMO_PERKS
