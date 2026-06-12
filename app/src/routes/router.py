from __future__ import annotations

from fastapi import APIRouter

from src.routes.health import router as health_router


def create_api_router() -> APIRouter:
    """Create the central API router registry for the application."""
    api_router = APIRouter()
    api_router.include_router(health_router)
    return api_router
