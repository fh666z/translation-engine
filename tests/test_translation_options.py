from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes_translation import router as translation_router
from translation_engine.domain.models import TranslationResult


class CapturingPipeline:
    def __init__(self) -> None:
        self.last_request = None
        self.context_ready = False
        self.translator = type(
            "FakeTranslator",
            (),
            {
                "config": type(
                    "FakeTranslationConfig",
                    (),
                    {
                        "target_language": "German",
                        "tone": "Neutral",
                        "purpose_of_text": "Informational",
                        "target_audience": "General public",
                    },
                )()
            },
        )()

    def execute(self, request):
        self.last_request = request
        return TranslationResult(
            source_text=request.text,
            initial_translation="Hallo",
            reflection=None,
            final_translation="Hallo",
            refinement_skipped=True,
            context_used=False,
        )

    def translate_simple(self, text: str, use_context: bool = True) -> str:
        return "Hallo"


@dataclass
class FakeEngine:
    pipeline: CapturingPipeline


def create_test_client(pipeline: CapturingPipeline) -> TestClient:
    app = FastAPI()
    app.include_router(translation_router)
    app.state.engine = FakeEngine(pipeline=pipeline)
    return TestClient(app)


def test_translate_route_passes_runtime_translation_options_into_domain_request():
    pipeline = CapturingPipeline()
    client = create_test_client(pipeline)

    response = client.post(
        "/api/v1/translate",
        json={
            "text": "Hello world",
            "source_language": "English",
            "target_language": "German",
            "tone": "Friendly",
            "purpose_of_text": "Marketing",
            "use_context": False,
            "use_reflection": True,
        },
    )

    assert response.status_code == 200
    options = getattr(pipeline.last_request, "options", None)
    assert options is not None
    assert options.source_language == "English"
    assert options.target_language == "German"
    assert options.tone == "Friendly"
    assert options.purpose_of_text == "Marketing"

