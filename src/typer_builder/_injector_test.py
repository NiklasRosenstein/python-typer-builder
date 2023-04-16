import pytest

from typer_builder._injector import DependencyInjectionError, DependencyInjector


def test_dependency_injector_raises_error_for_undeclared_dependency() -> None:
    injector = DependencyInjector()

    with pytest.raises(DependencyInjectionError):
        injector.get(int)


def test_dependency_injector_raises_error_for_undefined_dependency() -> None:
    injector = DependencyInjector()
    injector.declare(int)

    with pytest.raises(DependencyInjectionError):
        injector.get(int)


def test_dependency_injector_returns_dependency() -> None:
    injector = DependencyInjector()
    injector.set(int, 1)

    assert injector.get(int) == 1


def test_dependency_injector_returns_correct_value_from_dependency_registered_as_supplier() -> None:
    injector = DependencyInjector()
    injector.set_supplier(int, lambda: 1)

    assert injector.get(int) == 1


def test_dependency_injector_resolves_delayed_dependency() -> None:
    injector = DependencyInjector()
    injector.declare(int)
    injector.declare(str)

    @injector.bind
    def foo(x: int, y: str) -> str:
        return f"{x} {y}"

    injector.set(int, 1)
    injector.set(str, "two")

    assert foo() == "1 two"


def test_dependency_injector_resolves_updated_dependency() -> None:
    injector = DependencyInjector()
    injector.set(int, 1)
    injector.declare(str)

    @injector.bind
    def foo(x: int, y: str) -> str:
        return f"{x} {y}"

    injector.set(str, "two")

    assert foo() == "1 two"

    injector.set(int, 2)
    injector.set(str, "three")

    assert foo() == "2 three"


def test_dependency_injector_raises_error_on_undeclared_dependency() -> None:
    injector = DependencyInjector()

    with pytest.raises(DependencyInjectionError):

        @injector.bind
        def foo(x: int) -> int:
            return x


def test_dependency_injector_raises_error_on_undefined_dependency() -> None:
    injector = DependencyInjector()
    injector.declare(int)

    @injector.bind
    def foo(x: int) -> int:
        return x

    with pytest.raises(DependencyInjectionError) as excinfo:
        foo()
    assert str(excinfo.value) == "unable to provide a dependency for type int, but the type was declared"


def test_dependency_injector_unresolved_defaults() -> None:
    injector = DependencyInjector()

    @injector.bind
    def foo(x: int = 42) -> int:
        return x

    assert foo() == 42


def test_dependency_injector_allow_unresolved_binding() -> None:
    injector = DependencyInjector()

    @injector.bind(allow_unresolved=True)
    def foo(x: int) -> int:
        return x

    assert foo(42) == 42
