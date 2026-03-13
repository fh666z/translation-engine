from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes_frontend import router as frontend_router
from translation_engine.config.models import ContextConfig, TranslationConfig
from translation_engine.domain.models import TranslationResult


@dataclass
class FakeConfig:
    translation: TranslationConfig
    context: ContextConfig


class FakePipeline:
    def __init__(self) -> None:
        self.last_request = None

    def initialize_context(self, force: bool = False) -> bool:
        return True

    def execute(self, request):
        self.last_request = request
        return TranslationResult(
            source_text=request.text,
            initial_translation="Hallo Welt",
            reflection=None,
            final_translation="Hallo Welt",
            refinement_skipped=True,
            context_used=False,
        )


@dataclass
class FakeEngine:
    config: FakeConfig
    pipeline: FakePipeline
    context_provider: object | None = None


def create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(frontend_router)
    app.state.engine = FakeEngine(
        config=FakeConfig(
            translation=TranslationConfig(
                source_language="French",
                target_language="Spanish",
                target_audience="General public",
                tone="Neutral",
                purpose_of_text="Informational",
                specific_vocabulary_preferences="",
                cultural_considerations="",
                length_constraints="",
                key_phrases_to_preserve="",
                instructions="None",
            ),
            context=ContextConfig(
                enabled=False,
                embedding_model="embeddinggemma",
                chunk_size=1000,
                chunk_overlap=50,
                top_k=3,
                max_context_length=2000,
                websites=[],
            ),
        ),
        pipeline=FakePipeline(),
    )
    return TestClient(app)


def test_frontend_submission_uses_submitted_languages_in_result_badge():
    client = create_test_client()

    response = client.post(
        "/translate",
        data={
            "text": "Hello world",
            "source_language": "English",
            "target_language": "German",
            "tone": "Friendly",
            "purpose_of_text": "Marketing",
            "use_reflection": "on",
        },
    )

    assert response.status_code == 200
    assert "English → German" in response.text

