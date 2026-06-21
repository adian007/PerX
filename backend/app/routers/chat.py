"""Ask PerX chat — employee benefits consultant powered by Ollama gemma2:2b."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.database import get_db
from app.middleware.rate_limit import enforce_user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponseData
from app.schemas.recommendations import ApiEnvelope
from app.services.chat import answer_benefits_question
from app.utils.envelope import envelope

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ApiEnvelope)
async def ask_perx(
    body: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.employee))],
    _: Annotated[None, Depends(enforce_user_rate_limit)],
) -> dict:
    """Answer an employee benefits question using gemma2:2b with profile context."""

    reply, model, source, actions = await answer_benefits_question(
        db, current_user, body.message, body.history
    )
    return envelope(
        ChatResponseData(
            reply=reply,
            model=model,
            source=source,
            actions=actions,
        ).model_dump()
    )
