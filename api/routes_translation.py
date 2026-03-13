"""Translation-related API routes."""

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    TranslateRequest,
    TranslateResponse,
    TranslateSimpleRequest,
    TranslateSimpleResponse,
)
from translation_engine.domain.models import (
    TranslationOptions,
    TranslationRequest as DomainTranslationRequest,
)
from translation_engine.errors import ProviderUnavailableError
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
        options=TranslationOptions(
            source_language=payload.source_language or "Auto-detect",
            target_language=payload.target_language or pipeline.translator.config.target_language,
            tone=payload.tone or pipeline.translator.config.tone,
            purpose_of_text=payload.purpose_of_text or pipeline.translator.config.purpose_of_text,
            target_audience=pipeline.translator.config.target_audience,
            auto_detect_source_language=payload.auto_detect_source_language
            or (payload.source_language or "").lower() == "auto",
        ),
    )
    try:
        result = pipeline.execute(request)
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
    try:
        translation = pipeline.translate_simple(
            payload.text,
            use_context=payload.use_context,
            options=TranslationOptions(
                source_language=payload.source_language or "Auto-detect",
                target_language=payload.target_language or pipeline.translator.config.target_language,
                tone=payload.tone or pipeline.translator.config.tone,
                purpose_of_text=payload.purpose_of_text or pipeline.translator.config.purpose_of_text,
                target_audience=pipeline.translator.config.target_audience,
                auto_detect_source_language=payload.auto_detect_source_language
                or (payload.source_language or "").lower() == "auto",
            ),
        )
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    # translate_simple internally uses context if available
    context_used = pipeline.context_ready and payload.use_context
    return TranslateSimpleResponse(
        translation=translation,
        context_used=context_used,
    )

