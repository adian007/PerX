"""Payment audit trail repository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus
from app.models.payment import Payment


async def create_payment(
    db: AsyncSession,
    *,
    perk_selection_id: uuid.UUID,
    provider_id: uuid.UUID,
    employer_id: uuid.UUID,
    amount_cents: int,
    currency_code: str,
) -> Payment:
    """Insert a pending simulated payment (append-only)."""

    payment = Payment(
        perk_selection_id=perk_selection_id,
        provider_id=provider_id,
        employer_id=employer_id,
        amount_cents=amount_cents,
        currency_code=currency_code,
        status=PaymentStatus.pending,
        simulated=True,
    )
    db.add(payment)
    await db.flush()
    return payment


async def complete_payment(db: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    """Mark a payment completed (status update only)."""

    payment = await db.scalar(select(Payment).where(Payment.id == payment_id))
    if payment is None:
        return None
    payment.status = PaymentStatus.completed
    payment.processed_at = datetime.now(timezone.utc)
    await db.flush()
    return payment


async def list_payments_for_selection(
    db: AsyncSession,
    selection_id: uuid.UUID,
) -> list[Payment]:
    """Return payments linked to a selection."""

    result = await db.scalars(
        select(Payment)
        .where(Payment.perk_selection_id == selection_id)
        .order_by(Payment.created_at)
    )
    return list(result.all())
