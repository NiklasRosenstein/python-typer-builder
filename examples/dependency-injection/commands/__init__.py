"""
An example CLI application using typer-builder that demonstrates how to use the dependency injection system.
"""

from pathlib import Path

from config import ConfigManager
from typer import Option

from typer_builder import DependencyInjector

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "myapp" / "config.json"


def callback(
    config_path: Path = Option(DEFAULT_CONFIG_PATH, help="Path to config file"),
    injector: DependencyInjector = DependencyInjector.Provides(ConfigManager),
) -> None:
    def get_config() -> ConfigManager:
        return ConfigManager.load(config_path)

    injector.set_supplier(ConfigManager, get_config)
