"""Service-layer RBAC helpers and org-scoping guards."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import EmployeeProfile
from app.models.employer import EmployerOrganization
from app.models.enums import UserRole
from app.models.perk import Perk
from app.models.provider import ProviderProfile
from app.models.user import User
from app.repositories.employee import get_employee_by_user_id
from app.repositories.employer import get_employer_by_user_id
from app.repositories.provider import get_provider_by_user_id


def assert_role(user: User, allowed_roles: set[UserRole]) -> None:
    """Raise FORBIDDEN when the user's role is not in the allowed set.

    PostgreSQL RLS on perk_selections (migration 005) is the database backstop for org scoping.
    """

    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Insufficient role for this operation",
                "details": {},
            },
        )


def ensure_role(user: User, role: UserRole | str) -> None:
    """Service-layer helper — enforce a single required role."""

    required = UserRole(role) if isinstance(role, str) else role
    assert_role(user, {required})


async def require_employee_profile(db: AsyncSession, user: User) -> EmployeeProfile:
    """Load the employee profile for an authenticated employee user."""

    assert_role(user, {UserRole.employee})
    profile = await get_employee_by_user_id(db, user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Employee profile not found",
                "details": {},
            },
        )
    return profile


async def require_employer_org(db: AsyncSession, user: User) -> EmployerOrganization:
    """Load the employer organization for an authenticated employer user."""

    assert_role(user, {UserRole.employer})
    employer = await get_employer_by_user_id(db, user.id)
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Employer organization not found",
                "details": {},
            },
        )
    return employer


async def require_provider_profile(db: AsyncSession, user: User) -> ProviderProfile:
    """Load the provider profile for an authenticated provider user."""

    assert_role(user, {UserRole.provider})
    provider = await get_provider_by_user_id(db, user.id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Provider profile not found",
                "details": {},
            },
        )
    return provider


def assert_employer_scope(user: User, employer_id: uuid.UUID, org: EmployerOrganization) -> None:
    """Ensure an employer user only accesses their own organization."""

    assert_role(user, {UserRole.employer})
    if org.id != employer_id or org.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Cross-organization access denied",
                "details": {},
            },
        )


def assert_provider_owns_perk(
    user: User,
    provider: ProviderProfile,
    perk: Perk,
) -> None:
    """Ensure a provider user only accesses their own perks."""

    if user.role == UserRole.admin:
        return
    assert_role(user, {UserRole.provider})
    if perk.provider_id != provider.id or provider.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Provider does not own this perk",
                "details": {},
            },
        )
