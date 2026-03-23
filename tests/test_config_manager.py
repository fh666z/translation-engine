from pathlib import Path
import textwrap

import pytest

from translation_engine.config.manager import ConfigManager


def _write(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def test_config_manager_loads_root_yaml_files_by_default():
    manager = ConfigManager()

    manager.load_all()

    assert manager.ollama.model
    assert manager.translation.target_language
    assert manager.context is not None


def test_config_manager_uses_translation_model_for_vertex_runtime_model(tmp_path: Path):
    _write(
        tmp_path / "config_translation.yaml",
        """
        defaults:
          translation_model: "gemini-1.5-flash"
        reflection:
          enabled: false
        prompts:
          system: "s"
          reflection_system: "r"
          refinement_system: "f"
        """,
    )
    _write(
        tmp_path / "config.yaml",
        """
        provider_type: "vertex_ai"
        vertex_ai:
          project_id: "proj"
          location: "europe-west1"
          model_id: "SHOULD_NOT_BE_USED"
          embedding_model_id: "text-embedding-004"
        ollama:
          model: "also-ignored"
          base_url: "http://localhost:11434"
          temperature: 0.7
          streaming: true
        app:
          name: "Test"
          show_emojis: true
        """,
    )
    _write(
        tmp_path / "config_context.yaml",
        """
        context_sources:
          enabled: false
        """,
    )

    manager = ConfigManager(config_dir=tmp_path)
    manager.load_all()

    assert manager.translation.translation_model == "gemini-1.5-flash"
    assert manager.vertex_ai.model_id == "gemini-1.5-flash"


def test_config_manager_requires_translation_model(tmp_path: Path):
    _write(
        tmp_path / "config_translation.yaml",
        """
        defaults:
          source_language: "English"
        reflection:
          enabled: false
        prompts:
          system: "s"
          reflection_system: "r"
          refinement_system: "f"
        """,
    )
    _write(
        tmp_path / "config.yaml",
        """
        provider_type: "ollama"
        ollama:
          model: "ignored"
          base_url: "http://localhost:11434"
          temperature: 0.7
          streaming: true
        app:
          name: "Test"
          show_emojis: true
        """,
    )
    _write(
        tmp_path / "config_context.yaml",
        """
        context_sources:
          enabled: false
        """,
    )

    manager = ConfigManager(config_dir=tmp_path)
    with pytest.raises(ValueError, match="defaults.translation_model"):
        manager.load_all()


def test_config_manager_handles_empty_context_yaml_with_defaults(tmp_path: Path):
    _write(
        tmp_path / "config_translation.yaml",
        """
        defaults:
          translation_model: "translategemma:4b"
        reflection:
          enabled: false
        prompts:
          system: "s"
          reflection_system: "r"
          refinement_system: "f"
        """,
    )
    _write(
        tmp_path / "config.yaml",
        """
        provider_type: "ollama"
        ollama:
          model: "ignored"
          base_url: "http://localhost:11434"
          temperature: 0.7
          streaming: true
        app:
          name: "Test"
          show_emojis: true
        """,
    )
    (tmp_path / "config_context.yaml").write_text("", encoding="utf-8")

    manager = ConfigManager(config_dir=tmp_path)
    manager.load_all()

    assert manager.context.enabled is False
    assert manager.context.chunk_size == 500

