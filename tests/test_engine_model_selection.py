from pathlib import Path
import textwrap

from translation_engine.config.manager import ConfigManager
from translation_engine.engine import _create_main_llm


def _write(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def test_create_main_llm_uses_translation_model_for_ollama(tmp_path: Path):
    _write(
        tmp_path / "config_translation.yaml",
        """
        defaults:
          translation_model: "translategemma:27b"
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
          model: "SHOULD_NOT_BE_USED"
          base_url: "http://localhost:11434"
          temperature: 0.7
          streaming: false
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
    llm = _create_main_llm(manager)

    assert llm.config.model == "translategemma:27b"
