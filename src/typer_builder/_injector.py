"""
Implement dependency injection resolution on functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import Any, Callable, Container, Dict, List, Set, Type, TypeVar, cast, get_type_hints

from nr.stream import Supplier

T = TypeVar("T")


class DependencyInjectionError(Exception):
    pass


class DependencyInjector:
    """
    Arranges for dependency injection based on function signatures.
    """

    @dataclass
    class _Declared:
        pass

    @dataclass
    class _Instance:
        value: Any

    @dataclass
    class _Supplier:
        value: Callable[[], Any]

    _mapping: Dict[Type[Any], _Declared | _Instance | _Supplier]
    _delayed: Set[Type[Any]]

    def __init__(self, *objects: object) -> None:
        self._mapping = {}
        self._delayed = set()
        for obj in objects:
            if type(obj) in self._mapping:
                raise TypeError(
                    "cannot populate dependency provider with multiple instances of the same type "
                    f"({type(obj).__name__})"
                )
            self._mapping[type(obj)] = self._Instance(obj)

    def declare(self, type_: Type[T]) -> None:
        """
        Declare that at a later point, an instance or supplier for the given *type_* will be registered.
        When a function is processed by #bound() and it references types that are only declared, the resolution
        of the type will occur at call time of the function.
        """

        if type_ in self._mapping:
            raise TypeError(f"slot for type {type_.__name__} is already allocated in dependency injector")
        self._mapping[type_] = self._Declared()

    def register_supplier(self, type_: Type[T], supplier: Callable[..., T]) -> None:
        """
        Register a supplier for a given type. Any arguments expected by the *supplier* are resolved
        using the same dependency injection mechanism.
        """

        existing = self._mapping.get(type_)
        if existing is not None and not isinstance(existing, self._Declared):
            raise TypeError(f"slot for type {type_.__name__} is already allocated in dependency injector")
        self._mapping[type_] = self._Supplier(Supplier.once(Supplier.of_callable(self.bind(supplier))).get)

    def get_dependency_for_type(self, type_: Type[T]) -> T:
        """
        Resolve the value of a given type.
        """

        if not isinstance(type_, type):
            raise DependencyInjectionError(f"cannot provide dependency for non-type: {type_!r}")

        if type_ == DependencyInjector:
            return cast(T, self)

        if type_ in self._mapping:
            value = self._mapping[type_]
            if isinstance(value, self._Declared):
                raise DependencyInjectionError(
                    f"unable to provide a dependency for type {type_.__name__}, but the type was declared"
                )
            elif isinstance(value, self._Supplier):
                return cast(T, value.value())
            else:
                return cast(T, value.value)

        raise DependencyInjectionError(f"unable to provide a dependency for type {type_.__name__}")

    def bind(
        self,
        func: Callable[..., Any],
        allow_unresolved: bool = False,
        ignore: Container[str] = (),
    ) -> Callable[..., Any]:
        """
        Bind dependencies requested through the annotations of *func*.

        :param func: The function to bind dependencies to.
        :param allow_unresolved: Allow unresolved parameters and keep them in the function signature.
        :param ignore: Ignore parameters with these names.
        """

        undefined = object()

        sig = signature(func)
        annotations = get_type_hints(func)
        return_annotation = annotations.pop("return", undefined)

        # Inject the dependencies.
        remaining = {}
        bindings = {}
        delayed = set()
        for key, value in list(annotations.items()):
            # TODO(NiklasRosenstein): We should probably somehow derive a new instance of the dependency
            #       injector that has the current one as a parent delegate instead of globally declaring
            #       the bindings defined here.
            default = sig.parameters[key].default
            if value == DependencyInjector and isinstance(default, _DelayedBinding):
                for type_ in default.types:
                    self.declare(type_)

            if key in ignore:
                remaining[key] = value
            elif isinstance(self._mapping.get(value), (self._Declared, self._Supplier)):
                delayed.add(key)
            else:
                try:
                    bindings[key] = self.get_dependency_for_type(value)
                except DependencyInjectionError:
                    if not allow_unresolved:
                        raise
                    remaining[key] = value

        if not allow_unresolved and remaining:
            raise DependencyInjectionError(...)  # TODO

        if return_annotation is not undefined:
            remaining["return"] = return_annotation

        if not bindings and not delayed:
            return func

        @wraps(func)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            for key in delayed:
                kwargs[key] = self.get_dependency_for_type(annotations[key])
            return func(*args, **kwargs, **bindings)

        _wrapper.__annotations__ = remaining
        _wrapper.__signature__ = sig.replace(parameters=[v for k, v in sig.parameters.items() if k not in bindings and k not in delayed])  # type: ignore[attr-defined]  # noqa: E501
        return _wrapper


@dataclass
class _DelayedBinding:
    types: List[Type[Any]]


def DelayedBinding(*types: Type[Any]) -> Any:
    """
    This function should be used as the default value on a parameter that expects a #DependencyInjector, indicating
    that the function will supply the injector with additional dependencies of the given types.
    """

    return _DelayedBinding(list(types))
