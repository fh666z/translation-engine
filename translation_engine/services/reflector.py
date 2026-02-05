"""
Reflector service for translation quality improvement.

Handles the reflection (critique) and refinement steps of the
translation pipeline.
"""

import logging

from translation_engine.config.models import (
    PromptsConfig,
    ReflectionConfig,
    TranslationConfig,
)
from translation_engine.domain.models import ReflectionResult
from translation_engine.providers.base import LLMProvider


logger = logging.getLogger(__name__)


class Reflector:
    """
    Service for critiquing and refining translations.
    
    Implements the reflection pattern:
    1. Review/critique a translation
    2. Determine if refinement is needed
    3. Refine the translation based on feedback
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        translation_config: TranslationConfig,
        reflection_config: ReflectionConfig,
        prompts: PromptsConfig,
    ):
        """
        Initialize the reflector service.
        
        Args:
            llm: LLM provider for text generation.
            translation_config: Translation settings for language info.
            reflection_config: Reflection-specific settings.
            prompts: Prompt templates for reflection and refinement.
        """
        self.llm = llm
        self.translation_config = translation_config
        self.reflection_config = reflection_config
        self.prompts = prompts
    
    @property
    def is_enabled(self) -> bool:
        """Check if reflection is enabled in configuration."""
        return self.reflection_config.enabled
    
    def _build_reflection_prompt(self, original: str, translation: str) -> str:
        """
        Build the reflection system prompt.
        
        Args:
            original: Original source text.
            translation: Translation to review.
        
        Returns:
            Formatted reflection prompt.
        """
        return self.prompts.reflection_system.format(
            SOURCE_LANG=self.translation_config.source_language,
            TARGET_LANG=self.translation_config.target_language,
            ORIGINAL_TEXT=original,
            TRANSLATION=translation,
            TONE=self.translation_config.tone,
            TARGET_AUDIENCE=self.translation_config.target_audience,
        )
    
    def _build_refinement_prompt(
        self,
        original: str,
        translation: str,
        feedback: str,
    ) -> str:
        """
        Build the refinement system prompt.
        
        Args:
            original: Original source text.
            translation: Initial translation.
            feedback: Reflection feedback to incorporate.
        
        Returns:
            Formatted refinement prompt.
        """
        return self.prompts.refinement_system.format(
            SOURCE_LANG=self.translation_config.source_language,
            TARGET_LANG=self.translation_config.target_language,
            ORIGINAL_TEXT=original,
            INITIAL_TRANSLATION=translation,
            REFLECTION_FEEDBACK=feedback,
        )
    
    def _should_skip_refinement(self, reflection_text: str) -> bool:
        """
        Check if reflection indicates translation is good enough to skip refinement.
        
        Args:
            reflection_text: The reflection feedback text.
        
        Returns:
            True if refinement should be skipped.
        """
        reflection_lower = reflection_text.lower()
        for keyword in self.reflection_config.skip_keywords:
            if keyword.lower() in reflection_lower:
                return True
        return False
    
    def reflect(self, original: str, translation: str) -> ReflectionResult:
        """
        Critique a translation and determine if refinement is needed.
        
        Args:
            original: The original source text.
            translation: The translation to review.
        
        Returns:
            ReflectionResult with feedback and is_excellent flag.
        """
        debug = self.reflection_config.debug_logging
        
        if debug:
            logger.debug("=" * 60)
            logger.debug("REFLECTION STEP - Starting critique")
            logger.debug("Original text: %s...", original[:100])
            logger.debug("Translation to review: %s...", translation[:100])
        
        system_prompt = self._build_reflection_prompt(original, translation)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please review this translation and provide feedback."},
        ]
        
        feedback = self.llm.generate(messages)
        is_excellent = self._should_skip_refinement(feedback)
        
        if debug:
            logger.debug("Reflection feedback: %s", feedback)
            logger.debug("Is excellent (skip refinement): %s", is_excellent)
            logger.debug("=" * 60)
        
        return ReflectionResult(feedback=feedback, is_excellent=is_excellent)
    
    def refine(self, original: str, translation: str, feedback: str) -> str:
        """
        Improve a translation based on reflection feedback.
        
        Args:
            original: The original source text.
            translation: The initial translation.
            feedback: Reflection feedback to incorporate.
        
        Returns:
            The refined translation.
        """
        debug = self.reflection_config.debug_logging
        
        if debug:
            logger.debug("=" * 60)
            logger.debug("REFINEMENT STEP - Improving translation")
            logger.debug("Feedback to apply: %s...", feedback[:200])
        
        system_prompt = self._build_refinement_prompt(original, translation, feedback)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please provide the improved translation."},
        ]
        
        refined = self.llm.generate(messages)
        
        if debug:
            logger.debug("Refined translation: %s", refined)
            logger.debug("=" * 60)
        
        return refined

