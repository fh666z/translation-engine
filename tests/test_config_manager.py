from translation_engine.config.manager import ConfigManager


def test_config_manager_loads_root_yaml_files_by_default():
    manager = ConfigManager()

    manager.load_all()

    assert manager.ollama.model
    assert manager.translation.target_language
    assert manager.context is not None

