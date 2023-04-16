from config import Config, ConfigManager


def main(name: str, age: int, *, config: ConfigManager) -> None:
    """
    Write your name and age to the configuration file.
    """

    config.data = Config(name=name, age=age)
    config.write()
