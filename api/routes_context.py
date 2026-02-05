"""Context index management routes."""

from fastapi import APIRouter, BackgroundTasks, Depends

from api.schemas import ContextStatusResponse
from translation_engine.engine import Engine

from .dependencies import get_engine


router = APIRouter(prefix="/api/v1/context", tags=["context"])


@router.get("/status", response_model=ContextStatusResponse)
def get_context_status(engine: Engine = Depends(get_engine)) -> ContextStatusResponse:
    """
    Return the status of the context index (enabled, ready, chunk count).
    """
    pipeline = engine.pipeline
    enabled = pipeline.context_enabled
    ready = pipeline.context_ready
    chunk_count = (
        engine.context_provider.chunk_count
        if ready and engine.context_provider is not None
        else None
    )
    return ContextStatusResponse(
        enabled=enabled,
        ready=ready,
        chunk_count=chunk_count,
    )


@router.post("/rebuild")
def rebuild_context_index(
    background_tasks: BackgroundTasks,
    engine: Engine = Depends(get_engine),
) -> dict:
    """
    Trigger a rebuild of the context index in the background.
    """
    background_tasks.add_task(engine.pipeline.initialize_context, True)
    return {"started": True}

