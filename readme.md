# typer-builder

  [Typer]: https://typer.tiangolo.com/

This package allows you to easily build a [Typer][] CLI application from a Python module hierarchy.

### Quickstart

```
$ tree src/mypackage/commands/
src/mypackage/
├── __init__.py
├── __main__.py
└── commands
    ├── __init__.py
    ├── hello.py
    └── bye.py
```

```py
# src/mypackage/commands/hello.py
def main(name: str) -> None:
    print("Hello,", name)
```

```py
# src/mypackage/__main__.py
from typer_builder import build_app_from_module

if __name__ == "__main__":
    app = build_app_from_module("mypackage.commands")
    app()
```

### Features

* Packages are treated as command groups and _may_ define a `def callback(): ...` (see `Typer.add_callback()`).
* Modules are treated as commands and _must_ define a `def main(): ...` (see `Typer.command()`).
* Underscores in package or module names are normalized to hyphens (e.g `my_command` -> `my-command`).
* Command(-group) help text is extracted from the package or module docstring, or from the `main()` docstring.
* [WIP] Improved and dynamic dependency injection.
* Support for new-style type hints in older versions of Python and Typer (e.g. `str | None`).

### Dependency Injection

The `typer_builder.DependencyInjector` is essentially a mapping of types to a corresponding implementation. It allows
you to bind any function to the given dependencies based on the function signature.

The `build_app_from_module()` takes a `dependencies` argument which populates a `DependencyInjector`. All `callback()`
and `main()` functions encountered and added to a `typer.Typer` object are first bound to the dependencies that can be
served by the injector.

The types for which injection can take place must be known in advance. If the implementation is not known in advance,
a `callback()` can accept the `DependencyInjector` as an argument and inform about the dependencies that will be
provided by the callback, allowing any of its subcommands to resolve it.

```py
# src/mypackages/commands/__init__.py
"""
This is a cool CLI that uses typer-builder.
"""

from mypackage.config import CliConfig
from pathlib import Path
from typer_builder import DependencyInjector, DelayedBinding
from typer import Option

def callback(
    config_file: Path = Option(Path("~/.config/mypackage.ini"), help="Path to the configuration file."),
    dependencies: DependencyInjector = DelayedBinding(CliConfig),
) -> None:
    dependencies.register_supplier(CliConfig, lambda: CliConfig.load(config_file))
```

```py
# src/mypackage/commands/hello.py
from mypackage.config import CliConfig

def main(name: str, config: CliConfig) -> None:
    # ...
```

In the above example, the `config` parameter is not passed by [Typer][], but instead by the `DependencyInjector` per the implementation in the previous `callback()` snippet.

__Known caveats__

* Only concrete types are supported (no `Optional[CliConfig]` or vice versa).

## New-style type hint support

Through `typeapi`, we can convert new-tyle type hints such as `str | None` or `list[int]` to their corresponding
representation using `typing` before the function signature is parsed by [Typer][]. Usually, ty

```py
# src/mypackage/commands/hello.py
from mypackage.config import CliConfig

def main(name: str | None = None) -> None:
    # ...
```
