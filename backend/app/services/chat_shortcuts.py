"""Deterministic chat shortcuts — faster and more accurate than LLM for known intents."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.schemas.chat import ChatAction
from app.services.employees import get_employee_budget
from app.services.gamification import JOURNEY_CATEGORIES, get_gamification_snapshot
from app.services.recommendation.context import load_recommendation_context
from app.services.recommendation.engine import affinity_for_employee, build_recommendation_payload
from app.services.wishlist import get_my_wishlist
from app.utils.ollama import EXPLANATION_STORE, get_fallback_explanation

if TYPE_CHECKING:
    pass

BUDGET_RE = re.compile(r"\b(budget|allowance|remaining|left|buxhet|mbetur)\b", re.I)
WISHLIST_RE = re.compile(r"\b(wishlist|saved|save[d]? perks?|ruajtur|t[eë] ruajtura)\b", re.I)
RECOMMEND_RE = re.compile(
    r"\b(recommend|recommended|recommendation|suggest|why these|pse .*rekomand)\b",
    re.I,
)
JOURNEY_RE = re.compile(
    r"\b(journey|path|roadmap|rrug[aë]|pyet[eë]sor|questionnaire|quiz progress|gamification|points|streak|xp)\b",
    re.I,
)
EXPLAIN_RE = re.compile(r"\b(explain|explanation|why me|personalized)\b", re.I)


async def try_chat_shortcut(
    db: AsyncSession,
    user: User,
    message: str,
) -> tuple[str, str, list[ChatAction]] | None:
    """Return (reply, source, actions) when message matches a shortcut intent."""

    text = message.strip()
    if not text:
        return None

    if BUDGET_RE.search(text):
        return await _budget_shortcut(db, user)
    if WISHLIST_RE.search(text):
        return await _wishlist_shortcut(db, user)
    if RECOMMEND_RE.search(text):
        return await _recommendations_shortcut(db, user)
    if JOURNEY_RE.search(text):
        return await _journey_shortcut(db, user)
    if EXPLAIN_RE.search(text):
        return await _explanation_shortcut(db, user)

    return None


async def _budget_shortcut(db: AsyncSession, user: User) -> tuple[str, str, list[ChatAction]]:
    budget = await get_employee_budget(db, user)
    reply = (
        f"You have {budget.remaining_formatted} remaining this period ({budget.currency_code}). "
        f"Allocated: {budget.allocated_formatted}. Spent: {budget.spent_formatted}."
    )
    actions = [
        ChatAction(type="link", label="Explore perks", href="/employee/explore"),
        ChatAction(type="link", label="View saved", href="/employee/saved"),
    ]
    return reply, "api", actions


async def _wishlist_shortcut(db: AsyncSession, user: User) -> tuple[str, str, list[ChatAction]]:
    perks = await get_my_wishlist(db, user)
    if not perks:
        reply = "Your saved list is empty. Browse Explore to heart perks you like."
        return reply, "api", [ChatAction(type="link", label="Explore perks", href="/employee/explore")]

    names = ", ".join(p["name"] for p in perks[:5])
    extra = f" (+{len(perks) - 5} more)" if len(perks) > 5 else ""
    reply = f"You have {len(perks)} saved perk(s): {names}{extra}."
    actions = [ChatAction(type="link", label="Open saved library", href="/employee/saved")]
    for perk in perks[:3]:
        actions.append(
            ChatAction(
                type="link",
                label=f"View {perk['name'][:40]}",
                href=f"/employee/explore?category={perk.get('category', '')}",
                perk_id=perk["id"],
                perk_name=perk["name"],
            )
        )
    return reply, "api", actions


async def _recommendations_shortcut(
    db: AsyncSession,
    user: User,
) -> tuple[str, str, list[ChatAction]]:
    employee, catalog, budget_remaining, ucb_counts = await load_recommendation_context(db, user)
    settings = get_settings()
    payload = await build_recommendation_payload(
        employee=employee,
        available_perks=catalog,
        background_tasks=BackgroundTasks(),
        budget_remaining_cents=budget_remaining,
        ucb_counts=ucb_counts,
        limit=3,
        settings=settings,
    )
    perks = payload.get("perks") or []
    if not perks:
        reply = "No recommendations right now. Try Explore or complete onboarding."
        return reply, "api", [ChatAction(type="link", label="Explore perks", href="/employee/explore")]

    lines = [f"Top picks for you ({payload.get('mode', 'cold_start')} mode):"]
    actions: list[ChatAction] = []
    for item in perks[:3]:
        name = item.get("name", "Perk")
        price = item.get("employee_price_formatted", "")
        reason = item.get("reason_text") or item.get("short_description") or ""
        lines.append(f"• {name} ({price}) — {reason[:80]}")
        perk_id = item.get("id")
        category = item.get("category", "")
        if perk_id:
            actions.append(
                ChatAction(
                    type="link",
                    label=f"View {name[:36]}",
                    href=f"/employee/explore?category={category}",
                    perk_id=perk_id,
                    perk_name=name,
                )
            )
            actions.append(
                ChatAction(
                    type="save_perk",
                    label=f"Save {name[:28]}",
                    perk_id=perk_id,
                    perk_name=name,
                )
            )
    actions.append(ChatAction(type="link", label="See all on Home", href="/employee"))
    return "\n".join(lines), "api", actions


async def _journey_shortcut(db: AsyncSession, user: User) -> tuple[str, str, list[ChatAction]]:
    snapshot = await get_gamification_snapshot(db, user)
    profile = await _employee_profile(db, user)
    from app.services.recommendation.mappers import employee_from_orm

    employee = employee_from_orm(profile)
    affinity = affinity_for_employee(employee)

    completed = set(snapshot.completed_path_nodes)
    quiz = snapshot.quiz_progress or {}
    lines = [
        f"Level {snapshot.level} ({snapshot.class_label}) · {snapshot.points_balance} points · "
        f"{snapshot.streak_days}-day streak.",
    ]
    actions = [ChatAction(type="link", label="Open benefit path", href="/employee/journey")]

    for cat in JOURNEY_CATEGORIES:
        pct = int(round(affinity.get(cat, 0.05) * 100))
        if cat in completed:
            status = "completed"
        else:
            score = quiz.get(cat, 0)
            status = f"quiz {score}/3" if score else "not started"
        lines.append(f"• {cat.title()}: {pct}% profile match — {status}")
        if cat not in completed:
            score = quiz.get(cat, 0)
            if 0 < score < 3:
                actions.append(
                    ChatAction(
                        type="link",
                        label=f"Continue {cat} questionnaire",
                        href=f"/employee/quiz/{cat}",
                    )
                )

    if not snapshot.completed_path_nodes:
        lines.append("Tip: finish the food category questionnaire to mark your first path step.")
        actions.append(
            ChatAction(type="link", label="Start food questionnaire", href="/employee/quiz/food")
        )

    return "\n".join(lines), "api", actions


async def _explanation_shortcut(db: AsyncSession, user: User) -> tuple[str, str, list[ChatAction]]:
    employee, catalog, budget_remaining, ucb_counts = await load_recommendation_context(db, user)
    affinity = affinity_for_employee(employee)
    top = max(affinity.items(), key=lambda item: item[1])[0] if affinity else "wellness"

    stored = EXPLANATION_STORE.get(str(employee.id))
    if stored:
        reply = stored
    else:
        reply = get_fallback_explanation(top, employee.first_name)

    actions = [
        ChatAction(type="link", label="View recommendations", href="/employee"),
        ChatAction(type="link", label="Explore perks", href="/employee/explore"),
    ]
    del catalog, budget_remaining, ucb_counts
    return reply, "api" if stored else "fallback", actions


async def _employee_profile(db: AsyncSession, user: User):
    from app.services.access_control import require_employee_profile

    return await require_employee_profile(db, user)
