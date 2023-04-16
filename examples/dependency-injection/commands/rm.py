from config import ConfigManager


def main(*, config: ConfigManager) -> None:
    """
    Remove the configuration file.
    """

    config.remove()
