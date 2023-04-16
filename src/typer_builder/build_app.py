from __future__ import annotations

import asyncio
from functools import wraps
from importlib import import_module
from inspect import Signature, iscoroutinefunction, signature
from pathlib import Path
from pkgutil import iter_modules
from typing import Any, Callable, Coroutine, Mapping, Sequence

from typeapi import get_annotations
from typer import Exit, Typer

from .Dependencies import Dependencies


def build_app_from_module(
    module_name: str,
    name: str | None = None,
    typer_options: Mapping[str, Any] | None = None,
    dependencies: Dependencies | Sequence[Any] = (),
    event_loop: asyncio.AbstractEventLoop | None = None,
) -> Typer:
    """
    Looks at the module given with *module_name* and adds subcommand groups or commands to the Typer *app* based on
    the contents. Packages with an `__init__.py` will create a subcommand group, where the docstring of that module
    is the help of the group. Python modules that don't start with an underscore will create a command in the current
    subcommand group.

    :param module_name: The module to create a #Typer application for. The module must be a package with submodules.
    :param name: Override the name of the root #Typer application.
    :param typer_options: Keyword arguments to pass to every #Typer creation.
    :param dependencies: A sequence of objects with unique types that are injected into commands based on their
        function signature.
    """

    if event_loop is None:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

    if not isinstance(dependencies, Dependencies):
        dependencies = Dependencies(*dependencies)

    module = import_module(module_name)
    assert module.__file__, f"module {module_name!r} has no __file__"
    assert Path(module.__file__).stem == "__init__", f"expected a package for {module_name!r}"

    name = name or module_name.rpartition(".")[-1].replace("_", "-")
    app = Typer(name=name, help=module.__doc__, **(typer_options or {}))

    if hasattr(module, "callback"):
        app.callback()(_prepare_typer_func(module.callback, dependencies, event_loop))

    for submodule_info in iter_modules(module.__path__, prefix=module_name + "."):
        submodule_name = submodule_info.name.rpartition(".")[-1]
        subcommand_name = submodule_name.replace("_", "-")
        module_spec = submodule_info.module_finder.find_spec(submodule_info.name, module.__path__)  # type: ignore
        submodule = import_module(submodule_info.name)
        assert module_spec is not None, f"unable to find module spec of {submodule_info.name!r}"
        assert module_spec.origin is not None, f"module spec of {submodule_info.name!r} has no origin"

        if Path(module_spec.origin).stem == "__init__":
            sub_app = build_app_from_module(
                submodule_info.name,
                typer_options=typer_options,
                dependencies=dependencies.fork(),
                event_loop=event_loop,
            )
            app.add_typer(sub_app)

        elif not submodule_name.startswith("_"):
            func = _prepare_typer_func(submodule.main, dependencies, event_loop)
            app.command(
                name=subcommand_name,
                help=func.__doc__ or submodule.__doc__,
            )(func)

    return app


def _prepare_typer_func(
    func: Callable[..., int | None], dependencies: Dependencies, event_loop: asyncio.AbstractEventLoop
) -> Callable[..., None]:
    func = _evaluate_type_hints(func)
    if iscoroutinefunction(func):
        func = _deasyncify(func, event_loop)
    func = dependencies.bind(func, allow_unresolved=True)
    func = _raise_non_zero_exit_code_as_exit(func)
    return func


def _evaluate_type_hints(func: Callable[..., Any]) -> Callable[..., Any]:
    annotations = get_annotations(func)
    sig = signature(func)
    sig = sig.replace(
        parameters=[p.replace(annotation=annotations.get(p.name, p.empty)) for p in sig.parameters.values()],
        return_annotation=annotations.get("return", Signature.empty),
    )
    func.__signature__ = sig  # type: ignore[attr-defined]
    func.__annotations__ = annotations
    return func


def _raise_non_zero_exit_code_as_exit(func: Callable[..., int | None]) -> Callable[..., None]:
    """
    Wraps a function to raise a #Exit exception at the end.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        result = func(*args, **kwargs)
        if isinstance(result, int):
            raise Exit(code=result)
        elif result is not None:
            raise RuntimeError("expected None or integer return value from command function")

    return wrapper


def _deasyncify(
    func: Callable[..., Coroutine[Any, Any, Any]], event_loop: asyncio.AbstractEventLoop
) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return event_loop.run_until_complete(func(*args, **kwargs))

    return wrapper
