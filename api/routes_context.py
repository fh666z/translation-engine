"""Context index management routes."""

from fastapi import APIRouter, BackgroundTasks, Depends

from api.schemas import (
    ContextStatusResponse,
    UpdateContextSourcesRequest,
)
from translation_engine.engine import Engine
from translation_engine.providers.context import FAISSContextProvider

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


@router.post("/sources", response_model=ContextStatusResponse)
def update_context_sources(
    payload: UpdateContextSourcesRequest,
    background_tasks: BackgroundTasks,
    engine: Engine = Depends(get_engine),
) -> ContextStatusResponse:
    """
    Update the list of websites used for the context index.

    Accepts up to 3 websites and schedules a rebuild of the FAISS index
    in the background. The updated configuration applies to subsequent
    translation requests handled by this application instance.
    """
    if not engine.context_provider:
        # Context is disabled in configuration.
        return ContextStatusResponse(enabled=False, ready=False, chunk_count=None)

    websites = payload.websites[:3]
    provider = engine.context_provider

    if isinstance(provider, FAISSContextProvider):
        provider.set_websites(
            [
                {
                    "name": w.name or w.url,
                    "url": str(w.url),
                    "description": w.description or "",
                }
                for w in websites
            ]
        )
        background_tasks.add_task(engine.pipeline.initialize_context, True)

    # Return updated status (may still be rebuilding, so ready can be False)
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

