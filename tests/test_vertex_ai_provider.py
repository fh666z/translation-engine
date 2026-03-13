import pytest

from translation_engine.config.models import VertexAIConfig
from translation_engine.providers.vertex_ai import VertexAILLMProvider


class EmptyResponseModel:
    def generate_content(self, prompt, stream: bool = False):
        return type("Response", (), {"text": ""})()


class ErrorModel:
    def generate_content(self, prompt, stream: bool = False):
        raise ValueError("boom")


def test_vertex_provider_raises_on_empty_text_response():
    provider = VertexAILLMProvider(
        VertexAIConfig(
            project_id="proj",
            location="loc",
            model_id="model",
        )
    )
    provider._model = EmptyResponseModel()

    with pytest.raises(RuntimeError, match="empty response"):
        provider.generate([{"role": "user", "content": "hello"}])


def test_vertex_provider_wraps_sdk_errors():
    provider = VertexAILLMProvider(
        VertexAIConfig(
            project_id="proj",
            location="loc",
            model_id="model",
        )
    )
    provider._model = ErrorModel()

    with pytest.raises(RuntimeError, match="Vertex AI generation failed"):
        provider.generate([{"role": "user", "content": "hello"}])

