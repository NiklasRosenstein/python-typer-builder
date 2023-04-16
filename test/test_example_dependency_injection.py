"""
An integration test for the example from the examples/dependency-injection folder.
"""

import tempfile
from pathlib import Path
from subprocess import run
from typing import Iterator

import pytest

EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "dependency-injection"


@pytest.fixture
def tempdir() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tempdir:
        yield Path(tempdir)


def test_example_dependency_injection(tempdir: Path) -> None:
    config_file = tempdir / "config.json"
    prefix = ["python", "main.py", "--config-path", str(config_file)]

    result = run([*prefix, "show"], cwd=EXAMPLE_DIR, capture_output=True)
    assert result.returncode == 0
    assert result.stdout == b"No configuration set.\n"

    result = run([*prefix, "set", "Alice", "17"], cwd=EXAMPLE_DIR, capture_output=True)
    assert result.returncode == 0

    result = run([*prefix, "show"], cwd=EXAMPLE_DIR, capture_output=True)
    assert result.returncode == 0
    assert result.stdout == b"Name: Alice\nAge: 17\n"

    result = run([*prefix, "rm"], cwd=EXAMPLE_DIR, capture_output=True)
    assert result.returncode == 0

    assert not config_file.exists()
