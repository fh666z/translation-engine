"""
Configuration dataclasses for typed configuration management.

These dataclasses provide type-safe access to configuration values
loaded from YAML files.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class OllamaConfig:
    """Ollama LLM configuration settings."""
    model: str
    base_url: str
    temperature: float
    streaming: bool


@dataclass
class AppConfig:
    """Application-level configuration settings."""
    name: str
    show_emojis: bool


@dataclass
class VertexAIConfig:
    """
    Vertex AI configuration settings for generative models and embeddings.
    
    This configuration is used when the engine is running against
    Google Cloud Vertex AI instead of a local Ollama server.
    """
    project_id: str
    location: str
    model_id: str
    embedding_model_id: Optional[str] = None


ProviderType = Literal["ollama", "vertex_ai"]


@dataclass
class TranslationConfig:
    """Translation defaults and parameters."""
    source_language: str
    target_language: str
    target_audience: str
    tone: str
    purpose_of_text: str
    specific_vocabulary_preferences: str
    cultural_considerations: str
    length_constraints: str
    key_phrases_to_preserve: str
    instructions: str
    translation_model: Optional[str] = None


@dataclass
class ReflectionConfig:
    """Reflection pipeline configuration."""
    enabled: bool
    use_separate_model: bool
    reflection_model: str
    skip_keywords: list[str] = field(default_factory=list)
    debug_logging: bool = False


@dataclass
class ContextConfig:
    """Context sources configuration for FAISS indexing."""
    enabled: bool
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    max_context_length: int
    websites: list[dict] = field(default_factory=list)


@dataclass
class PromptsConfig:
    """Translation prompt templates."""
    system: str
    reflection_system: str
    refinement_system: str

