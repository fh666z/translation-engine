"""Application-level exceptions for user-facing service failures."""


class TranslationEngineError(RuntimeError):
    """Base class for expected runtime errors in the translation engine."""


class ProviderUnavailableError(TranslationEngineError):
    """Raised when the configured LLM or embedding backend is unavailable."""

