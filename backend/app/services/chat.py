"""Ask PerX chat — gemma2:2b with employee benefit context."""

from __future__ import annotations

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.schemas.chat import ChatAction, ChatHistoryMessage
from app.services.access_control import require_employee_profile
from app.services.chat_shortcuts import try_chat_shortcut
from app.services.employees import get_employee_budget, get_employee_me
from app.services.gamification import get_gamification_snapshot
from app.services.perks import browse_catalog
from app.services.recommendation.context import load_recommendation_context
from app.services.recommendation.engine import affinity_for_employee, build_recommendation_payload
from app.services.recommendation.mappers import employee_from_orm
from app.utils.ollama import generate_chat_reply


async def build_employee_chat_context(db: AsyncSession, user: User) -> str:
    """Assemble a compact context block for the LLM system prompt."""

    me = await get_employee_me(db, user)
    budget = await get_employee_budget(db, user)
    profile = await require_employee_profile(db, user)
    employee = employee_from_orm(profile)
    affinity = affinity_for_employee(employee)

    top_categories = sorted(affinity.items(), key=lambda item: item[1], reverse=True)[:4]
    category_lines = ", ".join(f"{cat} {int(score * 100)}%" for cat, score in top_categories)

    try:
        gamification = await get_gamification_snapshot(db, user)
        gamification_line = (
            f"Level {gamification.level}, {gamification.points_balance} points, "
            f"{gamification.streak_days}-day streak, "
            f"path completed: {', '.join(gamification.completed_path_nodes) or 'none'}, "
            f"quiz scores: {gamification.quiz_progress or {}}"
        )
    except Exception:  # noqa: BLE001
        gamification_line = "Gamification: not loaded"

    employee, catalog, budget_remaining, ucb_counts = await load_recommendation_context(db, user)
    rec_payload = await build_recommendation_payload(
        employee=employee,
        available_perks=catalog,
        background_tasks=BackgroundTasks(),
        budget_remaining_cents=budget_remaining,
        ucb_counts=ucb_counts,
        limit=3,
        settings=get_settings(),
    )
    rec_lines = ", ".join(
        f"{p.get('name')} ({p.get('employee_price_formatted')})"
        for p in (rec_payload.get("perks") or [])[:3]
    ) or "none yet"

    perks = await browse_catalog(db, limit=5)
    perk_lines = ", ".join(p.name for p in perks) if perks else "none loaded yet"

    return f"""Employee: {me.first_name} {me.last_name}
Employer: {me.employer.organization_name}
Onboarding complete: {me.onboarding_completed}
Recommender mode: {me.recommender_mode}
Budget remaining: {budget.remaining_formatted} ({budget.currency_code})
Category affinity: {category_lines}
Top recommendations: {rec_lines}
{gamification_line}
Sample catalog perks: {perk_lines}"""


def _history_to_tuples(history: list[ChatHistoryMessage]) -> list[tuple[str, str]]:
    return [(item.role, item.content) for item in history[-6:]]


async def answer_benefits_question(
    db: AsyncSession,
    user: User,
    message: str,
    history: list[ChatHistoryMessage] | None = None,
) -> tuple[str, str, str, list[ChatAction]]:
    """Return (reply, model, source, actions) for an employee chat message."""

    prior = history or []
    shortcut = await try_chat_shortcut(db, user, message)
    if shortcut is not None:
        reply, source, actions = shortcut
        return reply, "shortcut", source, actions

    me = await get_employee_me(db, user)
    context = await build_employee_chat_context(db, user)
    reply, model, source = await generate_chat_reply(
        message=message,
        employee_name=me.first_name,
        context=context,
        history=_history_to_tuples(prior),
    )
    return reply, model, source, []


def perk_actions_from_reply_context(
    perk_id: str,
    perk_name: str,
    category: str = "",
) -> list[ChatAction]:
    """Helper for future LLM post-processing."""

    return [
        ChatAction(
            type="link",
            label=f"View {perk_name[:36]}",
            href=f"/employee/explore?category={category}" if category else "/employee/explore",
            perk_id=perk_id,
            perk_name=perk_name,
        ),
        ChatAction(
            type="save_perk",
            label=f"Save {perk_name[:28]}",
            perk_id=perk_id,
            perk_name=perk_name,
        ),
    ]
