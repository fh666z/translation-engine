from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_engine
from api.routes_translation import router as translation_router
from translation_engine.supported_languages import (
    TRANSLATION_LANGUAGE_OPTIONS,
    language_options_for_translation_model,
)


def test_translategemma_language_count_and_core_labels() -> None:
    opts = language_options_for_translation_model("translategemma")
    assert opts[0] == "Auto-detect"
    assert opts[1] == "English"
    assert len(opts) == 57  # Auto-detect + English + 55 WMT24++ targets
    assert "Icelandic" in opts
    assert "German" in opts


def test_get_supported_languages_uses_engine_translation_model() -> None:
    fake_engine = MagicMock()
    fake_engine.config.translation.translation_model = "translategemma"

    app = FastAPI()
    app.include_router(translation_router)
    app.dependency_overrides[get_engine] = lambda: fake_engine
    client = TestClient(app)

    response = client.get("/api/v1/translate/languages")
    assert response.status_code == 200
    data = response.json()
    assert data["languages"] == TRANSLATION_LANGUAGE_OPTIONS
    assert "Auto-detect" in data["languages"]
    assert "English" in data["languages"]
    assert len(data["languages"]) == len(TRANSLATION_LANGUAGE_OPTIONS)
