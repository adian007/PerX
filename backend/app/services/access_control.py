"""Service-layer RBAC helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.models.enums import UserRole
from app.models.user import User


def assert_role(user: User, allowed_roles: set[UserRole]) -> None:
    """Raise FORBIDDEN when the user's role is not in the allowed set.

    TODO(Day 3+): PostgreSQL RLS policies are the database backstop for org scoping.
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
