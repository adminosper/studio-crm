from __future__ import annotations

from fastapi import APIRouter

from src.routes.health import router as health_router
from src.routes.leads import router as leads_router
from src.routes.scoring_rules import router as scoring_rules_router
from src.routes.tenant_thresholds import router as tenant_thresholds_router


def create_api_router() -> APIRouter:
    """Create the central API router registry for the application."""
    api_router = APIRouter()
    api_router.include_router(health_router)
    api_router.include_router(tenant_thresholds_router)
    api_router.include_router(leads_router)
    api_router.include_router(scoring_rules_router)
    return api_router
