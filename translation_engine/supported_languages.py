"""
Language labels for API / HTML dropdowns, keyed by `translation_model` in config.

For `translategemma`, the target set follows the 55 languages and dialects in the
WMT24++ benchmark (Deutsch et al., ACL 2025 Findings), which Google cites as the
core evaluated coverage for TranslateGemma, plus ``English`` and ``Auto-detect``
for prompts and the HTML UI.
"""

from __future__ import annotations

# WMT24++ en→xx targets (Table 1) + Icelandic; display names aligned with the paper.
_TRANSLATEGEMMA_TARGETS_ALPHABETICAL: list[str] = [
    "Arabic (Egypt)",
    "Arabic (Saudi Arabia)",
    "Bengali",
    "Bulgarian",
    "Catalan",
    "Chinese (Simplified)",
    "Chinese (Traditional)",
    "Croatian",
    "Czech",
    "Danish",
    "Dutch",
    "Estonian",
    "Filipino",
    "Finnish",
    "French (Canada)",
    "French (France)",
    "German",
    "Greek",
    "Gujarati",
    "Hebrew",
    "Hindi",
    "Hungarian",
    "Icelandic",
    "Indonesian",
    "Italian",
    "Japanese",
    "Kannada",
    "Korean",
    "Latvian",
    "Lithuanian",
    "Malayalam",
    "Marathi",
    "Norwegian",
    "Persian (Iran)",
    "Polish",
    "Portuguese (Brazil)",
    "Portuguese (Portugal)",
    "Punjabi",
    "Romanian",
    "Russian",
    "Serbian",
    "Slovak",
    "Slovenian",
    "Spanish (Mexico)",
    "Swahili (Kenya)",
    "Swahili (Tanzania)",
    "Swedish",
    "Tamil",
    "Telugu",
    "Thai",
    "Turkish",
    "Ukrainian",
    "Urdu",
    "Vietnamese",
    "Zulu",
]

LANGUAGES_BY_TRANSLATION_MODEL: dict[str, list[str]] = {
    "translategemma": [
        "Auto-detect",
        "English",
        *_TRANSLATEGEMMA_TARGETS_ALPHABETICAL,
    ],
}


def _normalize_translation_model_key(model_id: str) -> str:
    return model_id.strip().lower().replace(" ", "_").replace("-", "_")


def language_options_for_translation_model(model_id: str | None) -> list[str]:
    """
    Return dropdown language labels for the given ``translation_model`` value
    from ``config_translation.yaml`` (``defaults.translation_model``).

    Unknown or empty model ids fall back to ``translategemma``.
    """
    if not model_id or not str(model_id).strip():
        return LANGUAGES_BY_TRANSLATION_MODEL["translategemma"]
    key = _normalize_translation_model_key(str(model_id))
    return LANGUAGES_BY_TRANSLATION_MODEL.get(
        key,
        LANGUAGES_BY_TRANSLATION_MODEL["translategemma"],
    )


# Default export for callers that do not load config (tests, static checks).
TRANSLATION_LANGUAGE_OPTIONS: list[str] = LANGUAGES_BY_TRANSLATION_MODEL[
    "translategemma"
]
