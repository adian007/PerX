"""Load recommendation context from the database for authenticated employees."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.perk import PerkInteraction
from app.models.recommendation import EmployeeProfile as RecEmployee
from app.models.recommendation import Perk as RecPerk
from app.models.user import User
from app.repositories.budget import get_current_allocation
from app.repositories.perk import list_catalog_perks
from app.services.access_control import require_employee_profile
from app.services.recommendation.mappers import employee_from_orm, perk_from_orm, ucb_counts_from_interactions


async def load_recommendation_context(
    db: AsyncSession,
    user: User,
) -> tuple[RecEmployee, list[RecPerk], int, dict[str, int]]:
    """Load employee profile, catalog perks, budget remaining, and UCB counts."""

    profile = await require_employee_profile(db, user)
    employee = employee_from_orm(profile)
    perks = [perk_from_orm(perk) for perk in await list_catalog_perks(db, limit=200)]

    allocation = await get_current_allocation(db, profile.id)
    budget_remaining = allocation.remaining_cents if allocation else 0

    interactions = await db.scalars(
        select(PerkInteraction).where(PerkInteraction.employee_id == profile.id)
    )
    ucb_counts = ucb_counts_from_interactions(
        [
            {
                "perk_id": str(row.perk_id),
                "recommendation_rank": row.recommendation_rank,
            }
            for row in interactions
        ]
    )

    return employee, perks, budget_remaining, ucb_counts
