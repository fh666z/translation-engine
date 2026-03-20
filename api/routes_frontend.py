"""Server-rendered HTML frontend for the Translation Engine."""

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from translation_engine.context_profiles import ContextProfile
from translation_engine.domain.models import TranslationOptions, TranslationRequest
from translation_engine.engine import Engine
from translation_engine.errors import ProviderUnavailableError
from translation_engine.supported_languages import language_options_for_translation_model

from .dependencies import get_engine


router = APIRouter(tags=["frontend"])

templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def show_form(request: Request, engine: Engine = Depends(get_engine)) -> HTMLResponse:
    """
    Render the main translation form with configuration defaults.
    """
    translation_cfg = engine.config.translation
    context_cfg = engine.config.context

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "defaults": translation_cfg,
            "context_enabled": context_cfg.enabled,
            "language_options": language_options_for_translation_model(
                engine.config.translation.translation_model,
            ),
            "result": None,
        },
    )


@router.post("/translate", response_class=HTMLResponse)
def submit_form(
    request: Request,
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    tone: str = Form(...),
    purpose_of_text: str = Form(...),
    use_reflection: bool = Form(False),
    use_context: bool = Form(False),
    website1: str | None = Form(None),
    website2: str | None = Form(None),
    website3: str | None = Form(None),
    context_profile_id: str | None = Form(None),
    engine: Engine = Depends(get_engine),
) -> HTMLResponse:
    """
    Handle translation form submission and render results.
    """
    # Collect up to 3 websites for context.
    websites = [w for w in [website1, website2, website3] if w]

    context_notice = None
    error_message = None
    if use_context and websites and engine.context_profile_store is not None:
        profile: ContextProfile
        if context_profile_id:
            existing = engine.context_profile_store.get(context_profile_id)
            profile = (
                engine.context_profile_store.save(
                    ContextProfile(
                        id=context_profile_id,
                        websites=[
                            {"name": url, "url": url, "description": ""}
                            for url in websites[:3]
                        ],
                    )
                )
                if existing is not None
                else engine.context_profile_store.create(
                    [
                        {"name": url, "url": url, "description": ""}
                        for url in websites[:3]
                    ]
                )
            )
        else:
            profile = engine.context_profile_store.create(
                [
                    {"name": url, "url": url, "description": ""}
                    for url in websites[:3]
                ]
            )

        context_profile_id = profile.id
        if engine.context_provider is not None:
            background_tasks.add_task(
                engine.pipeline.initialize_context_profile,
                profile,
                True,
            )
            context_notice = (
                "Context profile saved. The website index is rebuilding in the "
                "background and may not be used until the next request."
            )

    translation_options = TranslationOptions(
        source_language=source_language,
        target_language=target_language,
        tone=tone,
        purpose_of_text=purpose_of_text,
        target_audience=engine.config.translation.target_audience,
        auto_detect_source_language=source_language.lower() == "auto-detect",
    )

    request_obj = TranslationRequest(
        text=text,
        use_context=use_context,
        use_reflection=use_reflection,
        options=translation_options,
        context_profile_id=context_profile_id,
    )
    result = None
    try:
        result = engine.pipeline.execute(request_obj)
    except ProviderUnavailableError as exc:
        error_message = str(exc)

    translation_cfg = engine.config.translation
    context_cfg = engine.config.context

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "defaults": translation_cfg,
            "context_enabled": context_cfg.enabled,
            "language_options": language_options_for_translation_model(
                engine.config.translation.translation_model,
            ),
            "result": result,
            "context_notice": context_notice,
            "error_message": error_message,
            "form": {
                "text": text,
                "source_language": source_language,
                "target_language": target_language,
                "tone": tone,
                "purpose_of_text": purpose_of_text,
                "use_reflection": use_reflection,
                "use_context": use_context,
                "websites": websites,
                "context_profile_id": context_profile_id,
            },
        },
    )

