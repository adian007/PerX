"""PostgreSQL enum types mirrored from database/migrations/001_initial.sql."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    employee = "employee"
    employer = "employer"
    provider = "provider"
    admin = "admin"


class PerkCategory(str, enum.Enum):
    fitness = "fitness"
    travel = "travel"
    wellness = "wellness"
    food = "food"
    education = "education"
    entertainment = "entertainment"
    transport = "transport"
    childcare = "childcare"
    other = "other"


class SelectionStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    expired = "expired"


class InteractionType(str, enum.Enum):
    view = "view"
    click = "click"
    detail_open = "detail_open"
    add_to_wishlist = "add_to_wishlist"
    remove_from_wishlist = "remove_from_wishlist"
    select = "select"
    reject = "reject"
    redeem = "redeem"


class BudgetPeriod(str, enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"
    one_time = "one_time"


class ProviderStatus(str, enum.Enum):
    pending_review = "pending_review"
    active = "active"
    suspended = "suspended"
    inactive = "inactive"


class NotificationType(str, enum.Enum):
    selection_approved = "selection_approved"
    selection_rejected = "selection_rejected"
    budget_low = "budget_low"
    new_perk = "new_perk"
    provider_update = "provider_update"
    system = "system"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
