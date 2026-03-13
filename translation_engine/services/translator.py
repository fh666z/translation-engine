"""
Translator service for text translation.

Handles the core translation functionality using an LLM provider
with configurable prompts and context.
"""

import logging
from dataclasses import replace
from typing import Iterator

from translation_engine.config.models import PromptsConfig, TranslationConfig
from translation_engine.domain.models import TranslationOptions
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
    
    def _resolve_config(
        self,
        options: TranslationOptions | None = None,
    ) -> tuple[TranslationConfig, str]:
        """
        Merge request-level translation options with YAML defaults.

        Returns a derived config object plus the source language label that
        should be shown in the prompt.
        """
        if options is None:
            return self.config, self.config.source_language

        source_language = options.source_language or self.config.source_language
        auto_detect = options.auto_detect_source_language or source_language.lower() == "auto"
        source_label = "Auto-detect" if auto_detect else source_language
        instructions = self.config.instructions
        if auto_detect:
            detect_instruction = (
                "Detect the source language automatically from the input text "
                "before translating."
            )
            instructions = (
                f"{instructions}\n{detect_instruction}"
                if instructions and instructions != "None"
                else detect_instruction
            )

        resolved = replace(
            self.config,
            source_language=source_label,
            target_language=options.target_language or self.config.target_language,
            tone=options.tone or self.config.tone,
            purpose_of_text=options.purpose_of_text or self.config.purpose_of_text,
            target_audience=options.target_audience or self.config.target_audience,
            instructions=instructions,
        )
        return resolved, source_label

    def _build_system_prompt(
        self,
        context: str = "",
        options: TranslationOptions | None = None,
    ) -> str:
        """
        Build the system prompt with configuration values.
        
        Args:
            context: Optional website context for terminology consistency.
        
        Returns:
            Formatted system prompt string.
        """
        resolved_config, source_label = self._resolve_config(options)
        system_prompt = self.prompts.system.format(
            SOURCE_LANG=source_label,
            SOURCE_CODE=source_label,
            TARGET_LANG=resolved_config.target_language,
            TARGET_CODE=resolved_config.target_language,
            TARGET_AUDIENCE=resolved_config.target_audience,
            TONE=resolved_config.tone,
            PURPOSE_OF_TEXT=resolved_config.purpose_of_text,
            SPECIFIC_VOCABULARY_PREFERENCES=resolved_config.specific_vocabulary_preferences,
            CULTURAL_CONSIDERATIONS=resolved_config.cultural_considerations,
            LENGTH_CONSTRAINTS=resolved_config.length_constraints,
            KEY_PHRASES_TO_PRESERVE=resolved_config.key_phrases_to_preserve,
            INSTRUCTIONS=resolved_config.instructions,
            WEBSITE_CONTEXT=context if context else "No additional context available.",
        )
        return system_prompt
    
    def _build_messages(
        self,
        text: str,
        context: str = "",
        options: TranslationOptions | None = None,
    ) -> list[dict]:
        """
        Build the message list for the LLM.
        
        Args:
            text: The source text to translate.
            context: Optional website context.
        
        Returns:
            List of message dicts for the LLM.
        """
        system_prompt = self._build_system_prompt(context, options)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
    
    def translate(
        self,
        text: str,
        context: str = "",
        options: TranslationOptions | None = None,
    ) -> str:
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
        
        messages = self._build_messages(text, context, options)
        return self.llm.generate(messages)
    
    def translate_stream(
        self,
        text: str,
        context: str = "",
        options: TranslationOptions | None = None,
    ) -> Iterator[str]:
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
        
        messages = self._build_messages(text, context, options)
        yield from self.llm.stream(messages)

