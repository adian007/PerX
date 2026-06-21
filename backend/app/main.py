"""FastAPI application factory for the PerX backend."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.middleware.rate_limit import enforce_auth_rate_limit
from app.routers import (
    admin,
    auth,
    chat,
    employees,
    employers,
    gamification,
    health,
    interactions,
    internal,
    notifications,
    onboarding,
    packages,
    perks,
    providers,
    recommendations,
    selections,
    websocket,
    vision,
)
from app.services.budget_reconcile import run_reconcile_loop
from app.utils.redis import close_redis, init_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks for shared clients."""

    settings = get_settings()
    await init_redis()
    from app.services.recommendation.cache import init_recommendation_cache

    await init_recommendation_cache()

    reconcile_task: asyncio.Task | None = None
    in_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
    if settings.reconcile_enabled and not in_pytest:
        reconcile_task = asyncio.create_task(
            run_reconcile_loop(interval_seconds=settings.reconcile_interval_seconds)
        )
        logger.info(
            "Budget reconcile loop started (interval=%ss)",
            settings.reconcile_interval_seconds,
        )

    yield

    if reconcile_task is not None:
        reconcile_task.cancel()
        try:
            await reconcile_task
        except asyncio.CancelledError:
            pass
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(title="PerX API", lifespan=lifespan)
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Internal-Key"],
    )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1", dependencies=[Depends(enforce_auth_rate_limit)])
    app.include_router(employees.router, prefix="/api/v1")
    app.include_router(gamification.router, prefix="/api/v1")
    app.include_router(employers.router, prefix="/api/v1")
    app.include_router(providers.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(perks.router, prefix="/api/v1")
    app.include_router(recommendations.router, prefix="/api/v1")
    app.include_router(onboarding.router, prefix="/api/v1")
    app.include_router(selections.router, prefix="/api/v1")
    app.include_router(packages.router, prefix="/api/v1")
    app.include_router(notifications.router, prefix="/api/v1")
    app.include_router(interactions.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(internal.router, prefix="/api/v1")
    app.include_router(websocket.router, prefix="/api/v1")
    app.include_router(vision.router, prefix="/api/v1")
    return app


app = create_app()
