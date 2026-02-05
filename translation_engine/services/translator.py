"""
Translator service for text translation.

Handles the core translation functionality using an LLM provider
with configurable prompts and context.
"""

import logging
from typing import Iterator

from translation_engine.config.models import PromptsConfig, TranslationConfig
from translation_engine.providers.base import LLMProvider


logger = logging.getLogger(__name__)


class Translator:
    """
    Service for translating text using an LLM.
    
    Builds prompts from configuration and context, then invokes
    the LLM provider to perform translation.
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        config: TranslationConfig,
        prompts: PromptsConfig,
    ):
        """
        Initialize the translator service.
        
        Args:
            llm: LLM provider for text generation.
            config: Translation configuration (languages, tone, etc.).
            prompts: Prompt templates for translation.
        """
        self.llm = llm
        self.config = config
        self.prompts = prompts
    
    def _build_system_prompt(self, context: str = "") -> str:
        """
        Build the system prompt with configuration values.
        
        Args:
            context: Optional website context for terminology consistency.
        
        Returns:
            Formatted system prompt string.
        """
        system_prompt = self.prompts.system.format(
            SOURCE_LANG=self.config.source_language,
            SOURCE_CODE=self.config.source_language,
            TARGET_LANG=self.config.target_language,
            TARGET_CODE=self.config.target_language,
            TARGET_AUDIENCE=self.config.target_audience,
            TONE=self.config.tone,
            PURPOSE_OF_TEXT=self.config.purpose_of_text,
            SPECIFIC_VOCABULARY_PREFERENCES=self.config.specific_vocabulary_preferences,
            CULTURAL_CONSIDERATIONS=self.config.cultural_considerations,
            LENGTH_CONSTRAINTS=self.config.length_constraints,
            KEY_PHRASES_TO_PRESERVE=self.config.key_phrases_to_preserve,
            INSTRUCTIONS=self.config.instructions,
            WEBSITE_CONTEXT=context if context else "No additional context available.",
        )
        return system_prompt
    
    def _build_messages(self, text: str, context: str = "") -> list[dict]:
        """
        Build the message list for the LLM.
        
        Args:
            text: The source text to translate.
            context: Optional website context.
        
        Returns:
            List of message dicts for the LLM.
        """
        system_prompt = self._build_system_prompt(context)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
    
    def translate(self, text: str, context: str = "") -> str:
        """
        Translate text using the LLM.
        
        Args:
            text: The source text to translate.
            context: Optional website context for terminology consistency.
        
        Returns:
            The translated text.
        """
        if context:
            logger.debug("Using website context (%d chars)", len(context))
        
        messages = self._build_messages(text, context)
        return self.llm.generate(messages)
    
    def translate_stream(self, text: str, context: str = "") -> Iterator[str]:
        """
        Translate text with streaming output.
        
        Args:
            text: The source text to translate.
            context: Optional website context.
        
        Yields:
            String chunks of the translation.
        """
        if context:
            logger.debug("Using website context (%d chars)", len(context))
        
        messages = self._build_messages(text, context)
        yield from self.llm.stream(messages)

