"""FastAPI application entrypoint for the Translation Engine API."""

import logging

from fastapi import FastAPI

from api.routes_context import router as context_router
from api.routes_health import router as health_router
from api.routes_translation import router as translation_router
from translation_engine.engine import create_engine


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Translation Engine API",
        version="1.0.0",
    )

    @app.on_event("startup")
    async def on_startup() -> None:
        """Initialize the translation engine on startup."""
        engine = create_engine()
        app.state.engine = engine
        logger.info("Translation engine initialized")

    # Routers
    app.include_router(translation_router)
    app.include_router(context_router)
    app.include_router(health_router)

    return app


app = create_app()

