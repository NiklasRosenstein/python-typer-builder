# typer-builder

  [Typer]: https://typer.tiangolo.com/
  [pep585]: https://www.python.org/dev/peps/pep-0585/
  [pep604]: https://www.python.org/dev/peps/pep-0604/
  [typeapi]: https://github.com/NiklasRosenstein/python-typeapi

A framework for simplifying the development of [Typer][] based CLIs supporting modern type hints and hierarchical
dependency injection. 

__Table of Contents__

* [Introduction](#introduction)
  * [Example](#example)
* [Documentation](#documentation)
  * [New-style type hint support](#new-style-type-hint-support)
  * [Dependency injection](#dependency-injection)


## Introduction

The `build_app_from_module()` inspect a hierarchy of Python modules to build a Typer command and group structure.
Packages are treated as command groups and may define a `callback()` member. Modules are treated commands and must
define a `main()` member. Modules and packages prefixed with an underscore ( `_` ) are ignored. Help text is extracted
from the `main()` docstring or the module docstring.

In addition, we provide support for new-style type hints ([PEP 585 - Type Hinting Generics in Standard Collections][pep585]
and [PEP 604 - Union Operators][pep604]) in older versions of Python as well as adapt it for Typer (e.g. `list[str]`
and `str | None`), as well as a method of injecting dependencies to functions that are not sourced from the command-line.


### Example

```
$ tree src/mypackage/
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


## Documentation

### New-style type hint support

Through [`typeapi`][typeapi], we can convert new-tyle type hints such as `str | None` or `list[int]` to their corresponding
representation using `typing` before the function signature is parsed by [Typer][].

```py
# src/mypackage/commands/create_user.py
from ___future__ import annotations

def main(name: str | None = None, groups: list[str] | None = None) -> None:
    # ...
```

[`typeapi`][typeapi] also allows us to convert `list[str]` to `List[str]` and `dict[str, int]` to `Dict[str, int]` for
Python versions prior to 3.9. This is necessary because [Typer][] does not support the new-style type hints.

### Dependency injection

The `typer_builder.Dependencies` object is used to map types to concrete values or functions that provide them.
Functions wrapped with `Dependencies.bind()` will have their arguments resolved by the injector based on type
annotations. Every `build_app_from_module()` call creates a new `Dependencies` instance. Dependencies can be
injected from the outside by passing a `Dependencies` instance to `build_app_from_module()` or by providing
additional dependencies via a `callback()` function on the command group.

Note that the `Dependencies` does not understand generics with different type parameters. For example, it makes
no distinction between `MyGeneric[int]` and `MyGeneric[str]`. This is a limitation of the current implementation as well
as the Python type system.

The most common use case for dependency injection is to inject configuration managers or clients into subcommands. For
an example, you should check out the [examples/dependency-injection](./examples/dependency-injection) directory.


## License

This project is licensed under the terms of the MIT license.
