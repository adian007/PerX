"""FastAPI application factory for the PerX backend."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import internal, onboarding, recommendations


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="PerX API")
    app.include_router(recommendations.router, prefix="/api/v1")
    app.include_router(onboarding.router, prefix="/api/v1")
    app.include_router(internal.router, prefix="/api/v1")
    return app


app = create_app()
