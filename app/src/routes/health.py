from __future__ import annotations

from fastapi import APIRouter

from src.config import get_settings
from src.models.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return a simple health-check payload for local verification."""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name)
