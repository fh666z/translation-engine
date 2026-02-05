"""Translation-related API routes."""

from fastapi import APIRouter, Depends

from api.schemas import (
    TranslateRequest,
    TranslateResponse,
    TranslateSimpleRequest,
    TranslateSimpleResponse,
)
from translation_engine.domain.models import TranslationRequest as DomainTranslationRequest
from translation_engine.services.pipeline import TranslationPipeline

from .dependencies import get_pipeline


router = APIRouter(prefix="/api/v1/translate", tags=["translation"])


@router.post("", response_model=TranslateResponse)
def translate(
    payload: TranslateRequest,
    pipeline: TranslationPipeline = Depends(get_pipeline),
) -> TranslateResponse:
    """
    Execute the full translation pipeline (translation + optional reflection).
    """
    request = DomainTranslationRequest(
        text=payload.text,
        use_context=payload.use_context,
        use_reflection=payload.use_reflection,
    )
    result = pipeline.execute(request)
    return TranslateResponse(
        source_text=result.source_text,
        initial_translation=result.initial_translation,
        reflection=result.reflection,
        final_translation=result.final_translation,
        refinement_skipped=result.refinement_skipped,
        context_used=result.context_used,
    )


@router.post("/simple", response_model=TranslateSimpleResponse)
def translate_simple(
    payload: TranslateSimpleRequest,
    pipeline: TranslationPipeline = Depends(get_pipeline),
) -> TranslateSimpleResponse:
    """
    Perform a simple translation without reflection.
    """
    translation = pipeline.translate_simple(
        payload.text,
        use_context=payload.use_context,
    )
    # translate_simple internally uses context if available
    context_used = pipeline.context_ready and payload.use_context
    return TranslateSimpleResponse(
        translation=translation,
        context_used=context_used,
    )

