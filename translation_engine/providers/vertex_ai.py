"""
Vertex AI-based implementations of LLM and Embedding providers.

These providers use the Google Cloud Vertex AI Python SDK to call
serverless generative models (e.g. Gemini, Gemma/TranslateGemma)
and text embedding models.
"""

from __future__ import annotations

from typing import Iterator, List

from google.cloud import aiplatform
from vertexai import init as vertexai_init
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel

from translation_engine.config.models import VertexAIConfig
from translation_engine.providers.base import EmbeddingProvider, LLMProvider


class VertexAILLMProvider(LLMProvider):
    """
    Vertex AI-based LLM provider.

    Wraps a Vertex AI GenerativeModel and exposes a simple
    generate/stream interface over chat-style messages.
    """

    def __init__(self, config: VertexAIConfig):
        self.config = config

        # Initialise Vertex AI with the configured project and location.
        vertexai_init(project=config.project_id, location=config.location)

        # Lazily initialised model handle.
        self._model = GenerativeModel(config.model_id)

    def _build_prompt(self, messages: list[dict]) -> str:
        """
        Convert chat-style messages into a single prompt string.

        This keeps things simple by concatenating system/user/assistant
        messages in order, marking their roles.
        """
        parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[SYSTEM]\n{content}\n")
            elif role == "assistant":
                parts.append(f"[ASSISTANT]\n{content}\n")
            else:
                parts.append(f"[USER]\n{content}\n")
        return "\n".join(parts).strip()

    def generate(self, messages: list[dict]) -> str:
        prompt = self._build_prompt(messages)
        response = self._model.generate_content(prompt)
        # Normalise to plain string output.
        return response.text or ""

    def stream(self, messages: list[dict]) -> Iterator[str]:
        prompt = self._build_prompt(messages)
        for chunk in self._model.generate_content(prompt, stream=True):
            if hasattr(chunk, "text") and chunk.text:
                yield chunk.text


class VertexAIEmbeddingProvider(EmbeddingProvider):
    """
    Vertex AI-based embedding provider using the text embedding models.

    This implementation is used for building the FAISS index when the
    engine is configured to run against Vertex AI instead of Ollama.
    """

    def __init__(self, config: VertexAIConfig):
        self.config = config
        if not config.embedding_model_id:
            raise ValueError(
                "VertexAIEmbeddingProvider requires embedding_model_id "
                "to be set in VertexAIConfig."
            )

        aiplatform.init(project=config.project_id, location=config.location)
        self._model = TextEmbeddingModel.from_pretrained(config.embedding_model_id)
        self._dimension: int | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.get_embeddings(texts)
        vectors: list[list[float]] = [e.values for e in embeddings]
        if vectors and self._dimension is None:
            self._dimension = len(vectors[0])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        [embedding] = self._model.get_embeddings([text])
        vector = embedding.values
        if self._dimension is None:
            self._dimension = len(vector)
        return vector

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Derive dimension lazily by creating a small test embedding.
            test_vec = self.embed_query("test")
            self._dimension = len(test_vec)
        return self._dimension

