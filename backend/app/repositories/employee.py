"""Employee profile repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import EmployeeProfile


async def get_employee_by_user_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> EmployeeProfile | None:
    """Load an employee profile by auth user id."""

    return await db.scalar(
        select(EmployeeProfile)
        .options(selectinload(EmployeeProfile.employer))
        .where(EmployeeProfile.user_id == user_id)
    )


async def get_employee_by_id(
    db: AsyncSession,
    employee_id: uuid.UUID,
) -> EmployeeProfile | None:
    """Load an employee profile by primary key."""

    return await db.scalar(
        select(EmployeeProfile)
        .options(selectinload(EmployeeProfile.employer))
        .where(EmployeeProfile.id == employee_id)
    )
