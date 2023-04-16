from config import ConfigManager


def main(*, config: ConfigManager) -> None:
    """
    Show the name and age from the configuration file.
    """

    if config.data is None:
        print("No configuration set.")
    else:
        print(f"Name: {config.data.name}")
        print(f"Age: {config.data.age}")
