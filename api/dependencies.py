"""FastAPI dependency helpers for accessing the translation engine."""

from fastapi import Depends, Request

from translation_engine.engine import Engine
from translation_engine.services.pipeline import TranslationPipeline


def get_engine(request: Request) -> Engine:
    """Retrieve the shared Engine instance from application state."""
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        # This should not happen if startup initialization succeeded
        raise RuntimeError("Translation engine is not initialized")
    return engine


def get_pipeline(engine: Engine = Depends(get_engine)) -> TranslationPipeline:
    """Dependency that returns the configured translation pipeline."""
    return engine.pipeline

