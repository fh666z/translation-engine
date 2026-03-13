"""
Translation pipeline orchestrator.

Coordinates the full translation workflow including context retrieval,
translation, reflection, and refinement.
"""

import logging
from typing import Iterator, Optional

from translation_engine.context_profiles import ContextProfile
from translation_engine.domain.models import TranslationRequest, TranslationResult
from translation_engine.providers.base import ContextProvider
from translation_engine.providers.context import FAISSContextProvider
from translation_engine.services.reflector import Reflector
from translation_engine.services.translator import Translator


logger = logging.getLogger(__name__)


class TranslationPipeline:
    """
    Orchestrates the complete translation workflow.
    
    The pipeline supports:
    1. Context retrieval from indexed websites
    2. Initial translation
    3. Reflection/critique of the translation
    4. Refinement based on feedback
    
    Each step can be enabled/disabled via the request or configuration.
    """
    
    def __init__(
        self,
        translator: Translator,
        reflector: Optional[Reflector] = None,
        context_provider: Optional[ContextProvider] = None,
    ):
        """
        Initialize the translation pipeline.
        
        Args:
            translator: Translator service for text translation.
            reflector: Optional reflector service for quality improvement.
            context_provider: Optional context provider for terminology consistency.
        """
        self.translator = translator
        self.reflector = reflector
        self.context_provider = context_provider
    
    @property
    def reflection_enabled(self) -> bool:
        """Check if reflection is available and enabled."""
        return self.reflector is not None and self.reflector.is_enabled
    
    @property
    def context_enabled(self) -> bool:
        """Check if context is available and enabled."""
        return (
            self.context_provider is not None
            and self.context_provider.is_enabled()
        )
    
    @property
    def context_ready(self) -> bool:
        """Check if context index is built and ready."""
        return (
            self.context_provider is not None
            and self.context_provider.is_ready()
        )
    
    def initialize_context(self, force: bool = False) -> bool:
        """
        Initialize the context index.
        
        Args:
            force: If True, rebuild the index even if already built.
        
        Returns:
            True if context is ready for use.
        """
        if not self.context_enabled:
            logger.info("Context is disabled")
            return False
        
        logger.info("Building context index...")
        return self.context_provider.build_index(force)

    def initialize_context_profile(
        self,
        profile: ContextProfile,
        force: bool = False,
    ) -> bool:
        """Build the FAISS index for a specific reusable context profile."""
        if not self.context_enabled:
            logger.info("Context is disabled")
            return False

        if not isinstance(self.context_provider, FAISSContextProvider):
            logger.info("Profile-based context is unavailable for this provider")
            return False

        logger.info("Building context index for profile %s...", profile.id)
        return self.context_provider.build_profile_index(
            profile_id=profile.id,
            websites=profile.websites,
            force=force,
        )
    
    def _get_context(self, text: str) -> str:
        """
        Get relevant context for translation.
        
        Args:
            text: The source text to find context for.
        
        Returns:
            Formatted context string, or empty if not available.
        """
        if not self.context_ready:
            return ""
        return self.context_provider.get_context(text)
    
    def execute(self, request: TranslationRequest) -> TranslationResult:
        """
        Execute the full translation pipeline.
        
        Steps:
        1. Get context if enabled and requested
        2. Perform initial translation
        3. If reflection enabled and requested:
           a. Reflect on translation
           b. Refine if not excellent
        
        Args:
            request: TranslationRequest with text and options.
        
        Returns:
            TranslationResult with all pipeline outputs.
        """
        # Step 1: Get context if enabled
        context = ""
        context_used = False
        if request.use_context:
            if (
                request.context_profile_id
                and isinstance(self.context_provider, FAISSContextProvider)
                and self.context_provider.is_profile_ready(request.context_profile_id)
            ):
                context = self.context_provider.get_profile_context(
                    request.context_profile_id,
                    request.text,
                )
            elif self.context_ready:
                context = self._get_context(request.text)
            context_used = bool(context)
            if context_used:
                logger.debug("Using context (%d chars)", len(context))
        
        # Step 2: Initial translation
        logger.debug("Step 1: Initial translation")
        initial_translation = self.translator.translate(
            request.text,
            context,
            request.options,
        )
        
        # Step 3: Reflection and refinement if enabled
        reflection_feedback = None
        final_translation = initial_translation
        refinement_skipped = True
        
        if request.use_reflection and self.reflection_enabled:
            logger.debug("Step 2: Reflection")
            reflection_result = self.reflector.reflect(
                request.text,
                initial_translation,
                request.options,
            )
            reflection_feedback = reflection_result.feedback
            
            if reflection_result.is_excellent:
                logger.debug("Step 3: Skipped - translation is excellent")
                refinement_skipped = True
            else:
                logger.debug("Step 3: Refinement")
                final_translation = self.reflector.refine(
                    request.text,
                    initial_translation,
                    reflection_feedback,
                    request.options,
                )
                refinement_skipped = False
        
        return TranslationResult(
            source_text=request.text,
            initial_translation=initial_translation,
            reflection=reflection_feedback,
            final_translation=final_translation,
            refinement_skipped=refinement_skipped,
            context_used=context_used,
        )
    
    def translate_simple(
        self,
        text: str,
        use_context: bool = True,
        options=None,
    ) -> str:
        """
        Perform a simple translation without reflection.
        
        Convenience method for quick translations.
        
        Args:
            text: The source text to translate.
            use_context: Whether to use context if available.
        
        Returns:
            The translated text.
        """
        context = ""
        if use_context and self.context_ready:
            context = self._get_context(text)
        
        return self.translator.translate(text, context, options)
    
    def translate_stream(
        self,
        text: str,
        use_context: bool = True,
        options=None,
    ) -> Iterator[str]:
        """
        Perform a streaming translation.
        
        Note: Streaming is not compatible with reflection pipeline.
        
        Args:
            text: The source text to translate.
            use_context: Whether to use context if available.
        
        Yields:
            String chunks of the translation.
        """
        context = ""
        if use_context and self.context_ready:
            context = self._get_context(text)
        
        yield from self.translator.translate_stream(text, context, options)

