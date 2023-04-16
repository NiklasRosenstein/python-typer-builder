from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Config:
    name: str
    age: int


@dataclass
class ConfigManager:
    data: Config | None
    path: Path

    @staticmethod
    def load(file: Path) -> "ConfigManager":
        if file.exists():
            config = ConfigManager(Config(**json.loads(file.read_text())), file)
        else:
            config = ConfigManager(None, file)
        return config

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.data is None:
            self.remove()
        else:
            self.path.write_text(json.dumps(asdict(self.data), indent=4))

    def remove(self) -> None:
        if self.path.is_file():
            self.path.unlink()
