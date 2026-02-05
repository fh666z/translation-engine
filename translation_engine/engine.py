"""
Engine initializer for the translation pipeline.

This module wires together configuration, providers, services, and the
translation pipeline into a reusable `Engine` object that can be used by
different frontends (FastAPI, CLI, etc.).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from translation_engine.config.manager import ConfigManager
from translation_engine.config.models import OllamaConfig
from translation_engine.providers.context import FAISSContextProvider
from translation_engine.providers.ollama import OllamaEmbeddingProvider, OllamaLLMProvider
from translation_engine.services.pipeline import TranslationPipeline
from translation_engine.services.reflector import Reflector
from translation_engine.services.translator import Translator


@dataclass
class Engine:
    """Container for the configured translation engine components."""
    config: ConfigManager
    llm: OllamaLLMProvider
    pipeline: TranslationPipeline
    context_provider: Optional[FAISSContextProvider] = None


def _create_main_llm(ollama_config: OllamaConfig) -> OllamaLLMProvider:
    """Create the primary LLM provider for translation."""
    return OllamaLLMProvider(ollama_config)


def _create_context_provider(
    config: ConfigManager,
) -> Optional[FAISSContextProvider]:
    """Create the context provider if context is enabled."""
    if not config.context.enabled:
        return None
    
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
    main_llm: OllamaLLMProvider,
) -> Optional[Reflector]:
    """Create the reflector service if reflection is enabled."""
    if not config.reflection.enabled:
        return None
    
    # Use separate model for reflection if configured
    if config.reflection.use_separate_model:
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
    llm = _create_main_llm(config.ollama)
    
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
    )

