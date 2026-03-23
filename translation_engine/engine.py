"""
Engine initializer for the translation pipeline.

This module wires together configuration, providers, services, and the
translation pipeline into a reusable `Engine` object that can be used by
different frontends (FastAPI, CLI, etc.).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from translation_engine.config.manager import ConfigManager
from translation_engine.config.models import OllamaConfig, VertexAIConfig
from translation_engine.context_profiles import InMemoryContextProfileStore
from translation_engine.providers.base import LLMProvider
from translation_engine.providers.context import FAISSContextProvider
from translation_engine.providers.ollama import OllamaEmbeddingProvider, OllamaLLMProvider
from translation_engine.services.pipeline import TranslationPipeline
from translation_engine.services.reflector import Reflector
from translation_engine.services.translator import Translator

if TYPE_CHECKING:
    from translation_engine.providers.vertex_ai import (
        VertexAIEmbeddingProvider,
        VertexAILLMProvider,
    )


@dataclass
class Engine:
    """Container for the configured translation engine components."""
    config: ConfigManager
    llm: LLMProvider
    pipeline: TranslationPipeline
    context_provider: Optional[FAISSContextProvider] = None
    context_profile_store: Optional[InMemoryContextProfileStore] = None


def _create_main_llm(config: ConfigManager) -> LLMProvider:
    """
    Create the primary LLM provider for translation based on configuration.
    
    Supports both local Ollama and Google Cloud Vertex AI backends.
    """
    translation_model = config.translation.translation_model
    if not translation_model:
        raise ValueError(
            "defaults.translation_model must be set in config_translation.yaml."
        )

    if config.provider_type == "vertex_ai":
        from translation_engine.providers.vertex_ai import VertexAILLMProvider

        vertex_base: VertexAIConfig = config.vertex_ai
        vertex_cfg = VertexAIConfig(
            project_id=vertex_base.project_id,
            location=vertex_base.location,
            model_id=translation_model,
            embedding_model_id=vertex_base.embedding_model_id,
        )
        return VertexAILLMProvider(vertex_cfg)
    # Default / local development: Ollama
    base_ollama_cfg: OllamaConfig = config.ollama
    ollama_cfg = OllamaConfig(
        model=translation_model,
        base_url=base_ollama_cfg.base_url,
        temperature=base_ollama_cfg.temperature,
        streaming=base_ollama_cfg.streaming,
    )
    return OllamaLLMProvider(ollama_cfg)


def _create_context_provider(
    config: ConfigManager,
) -> Optional[FAISSContextProvider]:
    """Create the context provider if context is enabled."""
    if not config.context.enabled:
        return None

    # Choose embedding backend based on provider_type.
    if config.provider_type == "vertex_ai":
        from translation_engine.providers.vertex_ai import VertexAIEmbeddingProvider

        embedding_provider = VertexAIEmbeddingProvider(config.vertex_ai)
    else:
        embedding_provider = OllamaEmbeddingProvider(
            model=config.context.embedding_model,
            base_url=config.ollama.base_url,
        )
    return FAISSContextProvider(
        config=config.context,
        embedding_provider=embedding_provider,
    )


def _create_reflector(
    config: ConfigManager,
    main_llm: LLMProvider,
) -> Optional[Reflector]:
    """Create the reflector service if reflection is enabled."""
    if not config.reflection.enabled:
        return None
    
    reflection_llm: LLMProvider
    # Use separate model for reflection if configured
    if config.reflection.use_separate_model:
        if config.provider_type == "vertex_ai":
            from translation_engine.providers.vertex_ai import VertexAILLMProvider

            # Use the same Vertex project/location but a different model id.
            vertex_base: VertexAIConfig = config.vertex_ai
            reflection_vertex_cfg = VertexAIConfig(
                project_id=vertex_base.project_id,
                location=vertex_base.location,
                model_id=config.reflection.reflection_model or vertex_base.model_id,
                embedding_model_id=vertex_base.embedding_model_id,
            )
            reflection_llm = VertexAILLMProvider(reflection_vertex_cfg)
        else:
            reflection_llm = OllamaLLMProvider(
                OllamaConfig(
                    model=config.reflection.reflection_model,
                    base_url=config.ollama.base_url,
                    temperature=config.ollama.temperature,
                    streaming=False,
                )
            )
    else:
        reflection_llm = main_llm
    
    return Reflector(
        llm=reflection_llm,
        translation_config=config.translation,
        reflection_config=config.reflection,
        prompts=config.prompts,
    )


def create_engine(config_dir: Optional[Path] = None) -> Engine:
    """
    Create and initialize the translation engine.
    
    Args:
        config_dir: Optional path to the directory containing YAML configs.
    
    Returns:
        Engine: fully configured engine with config, LLM, pipeline,
        and optional context provider.
    """
    # Load configuration
    config = ConfigManager(config_dir=config_dir)
    config.load_all()
    
    # Create main LLM provider
    llm = _create_main_llm(config)
    
    # Create context provider (if enabled)
    context_provider = _create_context_provider(config)
    
    # Create services
    translator = Translator(
        llm=llm,
        config=config.translation,
        prompts=config.prompts,
    )
    
    reflector = _create_reflector(config, llm)
    
    # Assemble pipeline
    pipeline = TranslationPipeline(
        translator=translator,
        reflector=reflector,
        context_provider=context_provider,
    )
    
    return Engine(
        config=config,
        llm=llm,
        pipeline=pipeline,
        context_provider=context_provider,
        context_profile_store=InMemoryContextProfileStore(),
    )

