"""SQLAlchemy ORM models — import all for Alembic autogenerate."""

from app.models.budget import BudgetAllocation
from app.models.employee import EmployeeProfile, EmployeeWishlist
from app.models.employer import EmployerOrganization
from app.models.enums import (
    BudgetPeriod,
    InteractionType,
    NotificationType,
    PaymentStatus,
    PerkCategory,
    ProviderStatus,
    SelectionStatus,
    UserRole,
)
from app.models.notification import Notification
from app.models.optimizer import OptimizerRun
from app.models.package import Package, PackageItem
from app.models.payment import Payment
from app.models.perk import Perk, PerkInteraction
from app.models.provider import ProviderProfile, ProviderRating
from app.models.selection import PerkSelection
from app.models.user import RefreshToken, User

__all__ = [
    "BudgetAllocation",
    "BudgetPeriod",
    "EmployeeProfile",
    "EmployeeWishlist",
    "EmployerOrganization",
    "InteractionType",
    "Notification",
    "NotificationType",
    "OptimizerRun",
    "Package",
    "PackageItem",
    "Payment",
    "PaymentStatus",
    "Perk",
    "PerkCategory",
    "PerkInteraction",
    "PerkSelection",
    "ProviderProfile",
    "ProviderRating",
    "ProviderStatus",
    "RefreshToken",
    "SelectionStatus",
    "User",
    "UserRole",
]
