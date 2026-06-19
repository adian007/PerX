"""Employer approval workflow."""

from __future__ import annotations

import uuid

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType, SelectionStatus, UserRole
from app.models.user import User
from app.repositories.budget import approve_budget_move, decrement_pending_cents
from app.repositories.selection import (
    get_selection_by_id,
    list_pending_approvals_for_org,
    resolve_approval_targets,
    set_selection_approved,
    set_selection_rejected,
)
from app.schemas.approvals import (
    ApprovalQueueEmployee,
    ApprovalQueueItem,
    ApprovalQueuePerk,
    ApproveResponseData,
    BulkApproveResponseData,
    RejectResponseData,
)
from app.services.access_control import assert_employer_scope, assert_role, require_employer_org
from app.services.budget import rollback_budget_decrement
from app.services.notifications import notify_user, send_push_if_configured
from app.services.payments import create_simulated_payment
from app.services.websocket_gateway import get_websocket_gateway
from app.utils.redis import RedisClient


def _ensure_pending_org_selection(selection, org_id: uuid.UUID) -> None:
    if selection.employer_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SELECTION_NOT_FOUND",
                "message": "Selection not found",
                "details": {},
            },
        )
    if selection.status != SelectionStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SELECTION_NOT_PENDING",
                "message": "Selection is not pending approval",
                "details": {"status": selection.status.value},
            },
        )


def _ensure_not_self_approval(selection, approver: User) -> None:
    employee_user_id = selection.employee.user_id
    if employee_user_id == approver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "SELF_APPROVAL_FORBIDDEN",
                "message": "You cannot approve your own selection",
                "details": {},
            },
        )


async def get_pending_approvals(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    per_page: int = 20,
) -> list[ApprovalQueueItem]:
    """Return pending approval queue for the employer's org only."""

    org = await require_employer_org(db, user)
    offset = (page - 1) * per_page
    rows = await list_pending_approvals_for_org(
        db,
        org.id,
        limit=per_page,
        offset=offset,
    )
    items: list[ApprovalQueueItem] = []
    for row in rows:
        allocation = row.budget_allocation
        remaining_after = (
            allocation.remaining_cents - row.price_cents_snapshot
            if allocation is not None
            else 0
        )
        employee = row.employee
        perk = row.perk
        items.append(
            ApprovalQueueItem(
                selection_id=str(row.id),
                package_id=str(row.package_id) if row.package_id else None,
                employee=ApprovalQueueEmployee(
                    id=str(employee.id),
                    name=f"{employee.first_name} {employee.last_name}",
                    department=employee.department,
                ),
                perk=ApprovalQueuePerk(
                    id=str(perk.id),
                    name=perk.name,
                    category=perk.category.value if hasattr(perk.category, "value") else str(perk.category),
                    image_url=perk.image_url,
                ),
                price_cents=row.price_cents_snapshot,
                budget_remaining_after_cents=remaining_after,
                selected_at=row.selected_at.isoformat(),
            )
        )
    return items


async def approve_selection(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    selection_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> ApproveResponseData:
    """Approve one selection (and package batch when applicable)."""

    assert_role(user, {UserRole.employer})
    org = await require_employer_org(db, user)
    selection = await get_selection_by_id(db, selection_id)
    if selection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SELECTION_NOT_FOUND",
                "message": "Selection not found",
                "details": {},
            },
        )

    assert_employer_scope(user, selection.employer_id, org)
    _ensure_pending_org_selection(selection, org.id)
    _ensure_not_self_approval(selection, user)

    targets = await resolve_approval_targets(db, selection, org.id)
    for target in targets:
        _ensure_pending_org_selection(target, org.id)

    notification_sent = False
    for target in targets:
        await approve_budget_move(db, target.budget_allocation_id, target.price_cents_snapshot)
        await set_selection_approved(db, target, approved_by=user.id)

    await notify_user(
        db,
        user_id=selection.employee.user_id,
        notification_type=NotificationType.selection_approved,
        title="Selection approved",
        body=f"Your selection for {selection.perk.name} has been approved.",
        data={
            "selection_id": str(selection.id),
            "package_id": str(selection.package_id) if selection.package_id else None,
            "approved_count": len(targets),
        },
    )
    notification_sent = await send_push_if_configured(
        selection.employee.user,
        title="Selection approved",
        body=f"Your selection for {selection.perk.name} has been approved.",
        data={"selection_id": str(selection.id)},
    )

    gateway = get_websocket_gateway()
    await gateway.broadcast_to_employee(
        str(selection.employee_id),
        "selection_approved",
        {
            "selection_id": str(selection.id),
            "perk_name": selection.perk.name,
            "approved_count": len(targets),
        },
    )

    background_tasks.add_task(create_simulated_payment, selection.id)

    return ApproveResponseData(
        status="approved",
        notification_sent=notification_sent,
        approved_count=len(targets),
    )


async def reject_selection(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    selection_id: uuid.UUID,
    *,
    reason: str,
) -> RejectResponseData:
    """Reject one selection (and package batch when applicable)."""

    assert_role(user, {UserRole.employer})
    org = await require_employer_org(db, user)
    selection = await get_selection_by_id(db, selection_id)
    if selection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SELECTION_NOT_FOUND",
                "message": "Selection not found",
                "details": {},
            },
        )

    assert_employer_scope(user, selection.employer_id, org)
    _ensure_pending_org_selection(selection, org.id)
    _ensure_not_self_approval(selection, user)

    targets = await resolve_approval_targets(db, selection, org.id)
    for target in targets:
        _ensure_pending_org_selection(target, org.id)

    notification_sent = False
    for target in targets:
        await decrement_pending_cents(db, target.budget_allocation_id, target.price_cents_snapshot)
        await rollback_budget_decrement(redis, target.budget_allocation, target.price_cents_snapshot)
        await set_selection_rejected(db, target, reason=reason)

    await notify_user(
        db,
        user_id=selection.employee.user_id,
        notification_type=NotificationType.selection_rejected,
        title="Selection rejected",
        body=reason,
        data={
            "selection_id": str(selection.id),
            "package_id": str(selection.package_id) if selection.package_id else None,
            "rejected_count": len(targets),
        },
    )
    notification_sent = await send_push_if_configured(
        selection.employee.user,
        title="Selection rejected",
        body=reason,
        data={"selection_id": str(selection.id)},
    )

    gateway = get_websocket_gateway()
    await gateway.broadcast_to_employee(
        str(selection.employee_id),
        "selection_rejected",
        {
            "selection_id": str(selection.id),
            "reason": reason,
            "rejected_count": len(targets),
        },
    )

    return RejectResponseData(
        status="rejected",
        notification_sent=notification_sent,
        rejected_count=len(targets),
    )


async def bulk_approve_selections(
    db: AsyncSession,
    redis: RedisClient,
    user: User,
    selection_ids: list[uuid.UUID],
    background_tasks: BackgroundTasks,
) -> BulkApproveResponseData:
    """Approve multiple selections; skips failures and deduplicates package batches."""

    assert_role(user, {UserRole.employer})
    org = await require_employer_org(db, user)

    approved = 0
    failed = 0
    seen_packages: set[uuid.UUID] = set()
    seen_selections: set[uuid.UUID] = set()

    for selection_id in selection_ids:
        if selection_id in seen_selections:
            continue

        selection = await get_selection_by_id(db, selection_id)
        if selection is None or selection.employer_id != org.id:
            failed += 1
            continue

        if selection.package_id is not None and selection.package_id in seen_packages:
            continue

        try:
            result = await approve_selection(
                db,
                redis,
                user,
                selection_id,
                background_tasks,
            )
            approved += result.approved_count
            seen_selections.add(selection_id)
            if selection.package_id is not None:
                seen_packages.add(selection.package_id)
                for target in await resolve_approval_targets(db, selection, org.id):
                    seen_selections.add(target.id)
        except HTTPException:
            failed += 1

    return BulkApproveResponseData(approved=approved, failed=failed)
