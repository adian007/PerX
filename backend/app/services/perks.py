"""Perk serialization helpers with role-aware field exclusion."""

from __future__ import annotations

from app.models.perk import Perk
from app.schemas.perks import PerkEmployeeRead, PerkProviderRead
from app.services.access_control import assert_role
from app.models.enums import UserRole
from app.models.user import User


def perk_for_employee(perk: Perk) -> PerkEmployeeRead:
    """Serialize a perk for employee-facing responses."""

    return PerkEmployeeRead.model_validate(perk)


def perk_for_provider(perk: Perk, user: User) -> PerkProviderRead:
    """Serialize a perk for provider/admin responses after role check."""

    assert_role(user, {UserRole.provider, UserRole.admin})
    return PerkProviderRead.model_validate(perk)
