"""Employer organization repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employer import EmployerOrganization


async def get_employer_by_user_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> EmployerOrganization | None:
    """Load employer organization for an auth user."""

    return await db.scalar(
        select(EmployerOrganization).where(EmployerOrganization.user_id == user_id)
    )


async def get_employer_by_id(
    db: AsyncSession,
    employer_id: uuid.UUID,
) -> EmployerOrganization | None:
    """Load employer organization by primary key."""

    return await db.scalar(
        select(EmployerOrganization).where(EmployerOrganization.id == employer_id)
    )
