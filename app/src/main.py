from __future__ import annotations

import logging

from fastapi import FastAPI

from src.config import get_settings
from src.routes.router import create_api_router

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.app_debug)
    app.include_router(create_api_router())
    return app


app = create_app()
