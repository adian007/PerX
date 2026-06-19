"""Simulated payment processing (ADR-007 Part 3)."""

from __future__ import annotations

import asyncio
import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.employee import EmployeeProfile
from app.models.enums import NotificationType, SelectionStatus
from app.models.selection import PerkSelection
from app.repositories.payment import complete_payment, create_payment
from app.services.notifications import notify_user, send_push_if_configured

logger = logging.getLogger(__name__)


async def create_simulated_payment(selection_id: uuid.UUID) -> None:
    """Background task: insert pending payments, delay, complete, notify employee."""

    async with AsyncSessionLocal() as db:
        try:
            selection = await db.scalar(
                select(PerkSelection)
                .options(
                    selectinload(PerkSelection.perk),
                    selectinload(PerkSelection.employee).selectinload(EmployeeProfile.user),
                )
                .where(PerkSelection.id == selection_id)
            )
            if selection is None or selection.status != SelectionStatus.approved:
                logger.warning("Skipping simulated payment; selection %s not approved", selection_id)
                return

            provider_amounts: dict[uuid.UUID, tuple[int, uuid.UUID, str]] = {}

            if selection.package_id is not None:
                batch = await db.scalars(
                    select(PerkSelection)
                    .options(selectinload(PerkSelection.perk))
                    .where(
                        PerkSelection.package_id == selection.package_id,
                        PerkSelection.employee_id == selection.employee_id,
                        PerkSelection.status == SelectionStatus.approved,
                    )
                )
                for row in batch.all():
                    provider_id = row.perk.provider_id
                    provider_amounts[provider_id] = (
                        row.price_cents_snapshot,
                        row.id,
                        row.currency_code,
                    )
            else:
                provider_amounts[selection.perk.provider_id] = (
                    selection.price_cents_snapshot,
                    selection.id,
                    selection.currency_code,
                )

            payment_ids: list[uuid.UUID] = []
            for provider_id, (amount, sel_id, currency) in provider_amounts.items():
                payment = await create_payment(
                    db,
                    perk_selection_id=sel_id,
                    provider_id=provider_id,
                    employer_id=selection.employer_id,
                    amount_cents=amount,
                    currency_code=currency,
                )
                payment_ids.append(payment.id)

            await db.flush()

            delay = random.uniform(1.0, 3.0)
            await asyncio.sleep(delay)

            completed = 0
            for payment_id in payment_ids:
                payment = await complete_payment(db, payment_id)
                if payment is not None:
                    completed += 1

            employee_user = selection.employee.user
            await notify_user(
                db,
                user_id=employee_user.id,
                notification_type=NotificationType.system,
                title="Payment confirmed",
                body="Your benefit payment has been processed successfully.",
                data={
                    "selection_id": str(selection_id),
                    "payments_completed": completed,
                    "package_id": str(selection.package_id) if selection.package_id else None,
                },
            )
            await send_push_if_configured(
                employee_user,
                title="Payment confirmed",
                body="Your benefit payment has been processed successfully.",
                data={"selection_id": str(selection_id)},
            )
            await db.commit()
        except Exception:
            logger.exception("Simulated payment failed for selection %s", selection_id)
            await db.rollback()
