from __future__ import annotations

from typing import List, Optional

from pytest import raises
from typer import Typer

from typer_builder.build_app import _evaluate_type_hints


def test__evaluate_type_hints() -> None:
    def func(value: str | None) -> list[str]:
        assert value == "foo"
        return [value]

    func = _evaluate_type_hints(func)

    assert func.__annotations__ == {"value": Optional[str], "return": List[str]}

    # Ensure that Typer can understand the type hints on the function now.
    app = Typer()
    app.command()(func)
    with raises(SystemExit) as excinfo:
        app(args=["foo"])
    assert excinfo.value.code == 0
