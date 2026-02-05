"""
Configuration manager for loading and validating YAML configuration files.

Provides centralized access to all configuration with type-safe dataclasses.
"""

from pathlib import Path
from typing import Optional

import yaml

from translation_engine.config.models import (
    AppConfig,
    ContextConfig,
    OllamaConfig,
    PromptsConfig,
    ReflectionConfig,
    TranslationConfig,
)


class ConfigManager:
    """
    Centralized configuration manager.
    
    Loads configuration from YAML files and provides typed access
    via dataclass properties.
    
    Usage:
        config = ConfigManager()
        config.load_all()
        print(config.ollama.model)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing config files. Defaults to project root.
        """
        self.config_dir = config_dir or Path(__file__).parent.parent
        
        # Configuration instances (populated by load_all)
        self._ollama: Optional[OllamaConfig] = None
        self._app: Optional[AppConfig] = None
        self._translation: Optional[TranslationConfig] = None
        self._reflection: Optional[ReflectionConfig] = None
        self._context: Optional[ContextConfig] = None
        self._prompts: Optional[PromptsConfig] = None
        
        # Raw config data for reference
        self._raw_main: dict = {}
        self._raw_translation: dict = {}
        self._raw_context: dict = {}
    
    def load_all(self) -> None:
        """Load all configuration files and populate dataclasses."""
        self._load_main_config()
        self._load_translation_config()
        self._load_context_config()
    
    def _load_main_config(self) -> None:
        """Load config.yaml (Ollama and app settings)."""
        config_file = self.config_dir / "config.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            self._raw_main = yaml.safe_load(f)
        
        ollama_data = self._raw_main.get("ollama", {})
        self._ollama = OllamaConfig(
            model=ollama_data.get("model", "translategemma"),
            base_url=ollama_data.get("base_url", "http://localhost:11434"),
            temperature=ollama_data.get("temperature", 0.7),
            streaming=ollama_data.get("streaming", True),
        )
        
        app_data = self._raw_main.get("app", {})
        self._app = AppConfig(
            name=app_data.get("name", "Translation Backend"),
            show_emojis=app_data.get("show_emojis", True),
        )
    
    def _load_translation_config(self) -> None:
        """Load config_translation.yaml (translation settings and prompts)."""
        config_file = self.config_dir / "config_translation.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Translation config file not found: {config_file}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            self._raw_translation = yaml.safe_load(f)
        
        defaults = self._raw_translation.get("defaults", {})
        self._translation = TranslationConfig(
            source_language=defaults.get("source_language", "English"),
            target_language=defaults.get("target_language", "German"),
            target_audience=defaults.get("target_audience", "General public"),
            tone=defaults.get("tone", "Professional"),
            purpose_of_text=defaults.get("purpose_of_text", "To inform"),
            specific_vocabulary_preferences=defaults.get("specific_vocabulary_preferences", ""),
            cultural_considerations=defaults.get("cultural_considerations", ""),
            length_constraints=defaults.get("length_constraints", ""),
            key_phrases_to_preserve=defaults.get("key_phrases_to_preserve", ""),
            instructions=defaults.get("instructions", "None"),
            translation_model=defaults.get("translation_model"),
        )
        
        reflection_data = self._raw_translation.get("reflection", {})
        self._reflection = ReflectionConfig(
            enabled=reflection_data.get("enabled", False),
            use_separate_model=reflection_data.get("use_separate_model", False),
            reflection_model=reflection_data.get("reflection_model", "translategemma"),
            skip_keywords=reflection_data.get("skip_keywords", [
                "excellent", "accurate", "no issues", "no changes needed"
            ]),
            debug_logging=reflection_data.get("debug_logging", False),
        )
        
        prompts_data = self._raw_translation.get("prompts", {})
        self._prompts = PromptsConfig(
            system=prompts_data.get("system", ""),
            reflection_system=prompts_data.get("reflection_system", ""),
            refinement_system=prompts_data.get("refinement_system", ""),
        )
    
    def _load_context_config(self) -> None:
        """Load config_context.yaml (context sources settings)."""
        config_file = self.config_dir / "config_context.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Context config file not found: {config_file}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            self._raw_context = yaml.safe_load(f)
        
        context_data = self._raw_context.get("context_sources", {})
        self._context = ContextConfig(
            enabled=context_data.get("enabled", False),
            embedding_model=context_data.get("embedding_model", "nomic-embed-text"),
            chunk_size=context_data.get("chunk_size", 500),
            chunk_overlap=context_data.get("chunk_overlap", 50),
            top_k=context_data.get("top_k", 3),
            max_context_length=context_data.get("max_context_length", 2000),
            websites=context_data.get("websites", []),
        )
    
    @property
    def ollama(self) -> OllamaConfig:
        """Get Ollama configuration."""
        if self._ollama is None:
            raise RuntimeError("Configuration not loaded. Call load_all() first.")
        return self._ollama
    
    @property
    def app(self) -> AppConfig:
        """Get application configuration."""
        if self._app is None:
            raise RuntimeError("Configuration not loaded. Call load_all() first.")
        return self._app
    
    @property
    def translation(self) -> TranslationConfig:
        """Get translation configuration."""
        if self._translation is None:
            raise RuntimeError("Configuration not loaded. Call load_all() first.")
        return self._translation
    
    @property
    def reflection(self) -> ReflectionConfig:
        """Get reflection configuration."""
        if self._reflection is None:
            raise RuntimeError("Configuration not loaded. Call load_all() first.")
        return self._reflection
    
    @property
    def context(self) -> ContextConfig:
        """Get context configuration."""
        if self._context is None:
            raise RuntimeError("Configuration not loaded. Call load_all() first.")
        return self._context
    
    @property
    def prompts(self) -> PromptsConfig:
        """Get prompts configuration."""
        if self._prompts is None:
            raise RuntimeError("Configuration not loaded. Call load_all() first.")
        return self._prompts

