"""Context index management routes."""

from fastapi import APIRouter, BackgroundTasks, Depends

from api.schemas import (
    ContextProfileResponse,
    ContextStatusResponse,
    UpdateContextSourcesRequest,
)
from translation_engine.context_profiles import ContextProfile
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


@router.post("/profiles", response_model=ContextProfileResponse)
def create_context_profile(
    payload: UpdateContextSourcesRequest,
    engine: Engine = Depends(get_engine),
) -> ContextProfileResponse:
    """
    Create a reusable context profile without rebuilding it yet.
    """
    if not engine.context_profile_store:
        raise RuntimeError("Context profile store is not initialized")

    websites = [
        {
            "name": website.name or str(website.url),
            "url": str(website.url),
            "description": website.description or "",
        }
        for website in payload.websites[:3]
    ]
    profile = engine.context_profile_store.create(websites)
    return ContextProfileResponse(profile_id=profile.id, ready=False, chunk_count=None)


@router.post("/profiles/{profile_id}/rebuild", response_model=ContextProfileResponse)
def rebuild_context_profile(
    profile_id: str,
    background_tasks: BackgroundTasks,
    engine: Engine = Depends(get_engine),
) -> ContextProfileResponse:
    """
    Trigger a background rebuild for a stored context profile.
    """
    if not engine.context_profile_store:
        raise RuntimeError("Context profile store is not initialized")

    profile: ContextProfile | None = engine.context_profile_store.get(profile_id)
    if profile is None:
        return ContextProfileResponse(profile_id=profile_id, ready=False, chunk_count=None)

    background_tasks.add_task(engine.pipeline.initialize_context_profile, profile, True)
    return ContextProfileResponse(profile_id=profile_id, ready=False, chunk_count=None)


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
    if not engine.context_profile_store:
        return ContextStatusResponse(enabled=False, ready=False, chunk_count=None)

    profile = engine.context_profile_store.create(
        [
            {
                "name": w.name or str(w.url),
                "url": str(w.url),
                "description": w.description or "",
            }
            for w in payload.websites[:3]
        ]
    )
    background_tasks.add_task(engine.pipeline.initialize_context_profile, profile, True)
    return ContextStatusResponse(enabled=True, ready=False, chunk_count=None)

