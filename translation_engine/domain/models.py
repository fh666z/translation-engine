"""
Domain models for translation requests and results.

These dataclasses represent the core domain objects passed between
services in the translation pipeline.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationOptions:
    """
    Request-level translation options that can override YAML defaults.
    
    This lets the API and HTML form change languages, tone, and purpose
    per request without mutating global configuration.
    """
    source_language: str
    target_language: str
    tone: str
    purpose_of_text: str
    target_audience: Optional[str] = None
    auto_detect_source_language: bool = False


@dataclass
class TranslationRequest:
    """
    Request object for translation operations.
    
    Encapsulates the source text and options for the translation pipeline.
    """
    text: str
    use_context: bool = True
    use_reflection: bool = True
    options: Optional[TranslationOptions] = None
    context_profile_id: Optional[str] = None


@dataclass
class ReflectionResult:
    """
    Result of the reflection/critique step.
    
    Contains the feedback and whether the translation was deemed excellent
    (in which case refinement can be skipped).
    """
    feedback: str
    is_excellent: bool  # True if translation is good enough to skip refinement


@dataclass
class TranslationResult:
    """
    Complete result of a translation operation.
    
    Contains all stages of the translation pipeline: initial translation,
    optional reflection feedback, and final translation.
    """
    source_text: str
    initial_translation: str
    reflection: Optional[str]  # None if reflection was disabled
    final_translation: str
    refinement_skipped: bool
    context_used: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "initial_translation": self.initial_translation,
            "reflection": self.reflection,
            "final_translation": self.final_translation,
            "refinement_skipped": self.refinement_skipped,
        }

