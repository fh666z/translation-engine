"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends

from api.schemas import HealthResponse
from translation_engine.engine import Engine

from .dependencies import get_engine


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(engine: Engine = Depends(get_engine)) -> HealthResponse:
    """
    Basic liveness/health endpoint.
    
    For now, this only checks that the engine has been initialized.
    """
    # Engine being resolved successfully is our primary health check here.
    _ = engine
    return HealthResponse(status="ok")

