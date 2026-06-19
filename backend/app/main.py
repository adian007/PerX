"""FastAPI application factory for the PerX backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.middleware.rate_limit import enforce_auth_rate_limit
from app.routers import access, auth, internal, onboarding, perks, recommendations
from app.utils.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks for shared clients."""

    await init_redis()
    yield
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
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    app.include_router(auth.router, prefix="/api/v1", dependencies=[Depends(enforce_auth_rate_limit)])
    app.include_router(access.router, prefix="/api/v1")
    app.include_router(perks.router, prefix="/api/v1")
    app.include_router(recommendations.router, prefix="/api/v1")
    app.include_router(onboarding.router, prefix="/api/v1")
    app.include_router(internal.router, prefix="/api/v1")
    return app


app = create_app()
