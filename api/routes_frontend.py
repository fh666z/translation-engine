"""Server-rendered HTML frontend for the Translation Engine."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from translation_engine.domain.models import TranslationOptions, TranslationRequest
from translation_engine.engine import Engine

from .dependencies import get_engine


router = APIRouter(tags=["frontend"])

templates = Jinja2Templates(directory="templates")

LANGUAGE_OPTIONS = [
    "Auto-detect",
    "English",
    "German",
    "Bulgarian",
    "French",
    "Spanish",
    "Italian",
    "Dutch",
    "Portuguese",
    "Romanian",
    "Greek",
]


@router.get("/", response_class=HTMLResponse)
def show_form(request: Request, engine: Engine = Depends(get_engine)) -> HTMLResponse:
    """
    Render the main translation form with configuration defaults.
    """
    translation_cfg = engine.config.translation
    context_cfg = engine.config.context

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "defaults": translation_cfg,
            "context_enabled": context_cfg.enabled,
            "language_options": LANGUAGE_OPTIONS,
            "result": None,
        },
    )


@router.post("/translate", response_class=HTMLResponse)
def submit_form(
    request: Request,
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
    engine: Engine = Depends(get_engine),
) -> HTMLResponse:
    """
    Handle translation form submission and render results.
    """
    # Collect up to 3 websites for context.
    websites = [w for w in [website1, website2, website3] if w]

    if use_context and websites and engine.context_provider is not None:
        # Update the context provider's websites and rebuild the index
        # synchronously for simplicity.
        from translation_engine.providers.context import FAISSContextProvider

        provider = engine.context_provider
        if isinstance(provider, FAISSContextProvider):
            provider.set_websites(
                [
                    {"name": url, "url": url, "description": ""}
                    for url in websites[:3]
                ]
            )
            engine.pipeline.initialize_context(force=True)

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
    )
    result = engine.pipeline.execute(request_obj)

    translation_cfg = engine.config.translation
    context_cfg = engine.config.context

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "defaults": translation_cfg,
            "context_enabled": context_cfg.enabled,
            "language_options": LANGUAGE_OPTIONS,
            "result": result,
            "form": {
                "text": text,
                "source_language": source_language,
                "target_language": target_language,
                "tone": tone,
                "purpose_of_text": purpose_of_text,
                "use_reflection": use_reflection,
                "use_context": use_context,
                "websites": websites,
            },
        },
    )

