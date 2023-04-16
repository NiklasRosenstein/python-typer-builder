"""
Implement dependency injection resolution on functions.
"""

from __future__ import annotations

from collections import ChainMap
from dataclasses import dataclass
from functools import wraps
from inspect import signature
from typing import Any, Callable, Container, List, MutableMapping, Type, TypeVar, cast, get_type_hints, overload

from deprecated import deprecated
from nr.stream import Supplier

T = TypeVar("T")


class Dependencies:
    """
    Arranges for dependency injection based on function signatures.
    """

    class Error(Exception):
        pass

    @dataclass
    class _Declared:
        pass

    @dataclass
    class _Instance:
        value: Any

    @dataclass
    class _Supplier:
        value: Callable[[], Any]

    @dataclass
    class _Provides:
        types: List[Type[Any]]

    _mapping: MutableMapping[Type[Any], _Declared | _Instance | _Supplier]

    def __init__(self, *objects: object, parent: Dependencies | None = None) -> None:
        self._parent = parent
        self._mapping = ChainMap({Dependencies: self._Instance(self)}, parent._mapping if parent else {})
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

    def get(self, type_: Type[T]) -> T:
        """
        Resolve the value of a given type.
        """

        if not isinstance(type_, type):
            raise Dependencies.Error(f"cannot provide dependency for non-type: {type_!r}")

        if type_ in self._mapping:
            value = self._mapping[type_]
            if isinstance(value, self._Declared):
                raise Dependencies.Error(
                    f"unable to provide a dependency for type {type_.__name__}, but the type was declared"
                )
            elif isinstance(value, self._Supplier):
                return cast(T, value.value())
            else:
                return cast(T, value.value)

        raise Dependencies.Error(f"unable to provide a dependency for type {type_.__name__}")

    def set(self, type_: Type[T], instance: T) -> None:
        """
        Register an instance for a given type.
        """

        self._mapping[type_] = self._Instance(instance)

    def set_supplier(self, type_: Type[T], supplier: Callable[..., T]) -> None:
        """
        Register a supplier for a given type. Any arguments expected by the *supplier* are resolved
        using the same dependency injection mechanism.
        """

        self._mapping[type_] = self._Supplier(Supplier.once(Supplier.of_callable(self.bind(supplier))).get)

    @deprecated(reason="use set_supplier() instead", version="0.0.8")
    def register_supplier(self, type_: Type[T], supplier: Callable[..., T]) -> None:
        """
        Deprecated. Use #set_supplier() instead.
        """

        self.set_supplier(type_, supplier)

    @deprecated(reason="use get() instead", version="0.0.8")
    def get_dependency_for_type(self, type_: Type[T]) -> T:
        """
        Deprecated. Use #get() instead.
        """

        return self.get(type_)

    @overload
    def bind(
        self,
        *,
        allow_unresolved: bool = False,
        ignore: Container[str] = (),
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        pass

    @overload
    def bind(
        self,
        func: Callable[..., Any],
        *,
        allow_unresolved: bool = False,
        ignore: Container[str] = (),
    ) -> Callable[..., Any]:
        pass

    def bind(
        self,
        func: Callable[..., Any] | None = None,
        *,
        allow_unresolved: bool = False,
        ignore: Container[str] = (),
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]] | Callable[..., Any]:
        """
        Bind function parameters to the dependencies provided by this injector per the function signature.

        The matching parameters of *func* for which a dependency can be resolved are resolved through #get()
        each time the returned function is called. The remaining parameters are left unbound as-is and the function
        signature is adjusted accordingly.

        :param func: The function to bind dependencies to.
        :param allow_unresolved: Allow unresolved parameters and keep them in the function signature.
        :param ignore: Ignore parameters with these names.
        """

        if func is None:
            return lambda func: self.bind(func, allow_unresolved=allow_unresolved, ignore=ignore)

        return self._resolve_arguments(func, allow_unresolved, ignore)

    def _resolve_arguments(
        self,
        func: Callable[..., Any],
        allow_unresolved: bool = False,
        ignore: Container[str] = (),
    ) -> Callable[..., Any]:
        """
        Bind function parameters to the dependencies provided by this injector per the function signature.

        The matching parameters of *func* for which a dependency can be resolved are resolved through #get()
        each time the returned function is called. The remaining parameters are left unbound as-is and the function
        signature is adjusted accordingly.

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
        bindings = set()
        for key, value in list(annotations.items()):
            # TODO(NiklasRosenstein): We should probably somehow derive a new instance of the dependency
            #       injector that has the current one as a parent delegate instead of globally declaring
            #       the bindings defined here.
            default = sig.parameters[key].default
            if value == Dependencies and isinstance(default, Dependencies._Provides):
                for type_ in default.types:
                    self.declare(type_)

            if key in ignore:
                remaining[key] = value
            elif value in self._mapping:
                bindings.add(key)
            elif not allow_unresolved and sig.parameters[key].default is sig.parameters[key].empty:
                raise Dependencies.Error(f"unable to provide dependency for {key!r} of type {value!r}")

        if not allow_unresolved and remaining:
            raise Dependencies.Error(f"unable to provide dependencies for {remaining}")

        if return_annotation is not undefined:
            remaining["return"] = return_annotation

        if not bindings:
            return func

        @wraps(func)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            for key in bindings:
                kwargs[key] = self.get(annotations[key])
            return func(*args, **kwargs)

        _wrapper.__annotations__ = remaining
        _wrapper.__signature__ = sig.replace(  # type: ignore[attr-defined]
            parameters=[v for k, v in sig.parameters.items() if k not in bindings]
        )
        return _wrapper

    @staticmethod
    def Provides(*types: Type[Any]) -> Any:
        """
        This function should be used as the default value on a parameter that expects a parameter that expects a
        #Dependencies, indicating that the function will supply the injector with additional dependencies of
        the given types.

        When a function is bound using #bind(), the injector will automatically declare the types given to this
        function as dependencies, so that they can be resolved by the injector. Note that this requires the
        function to be called at least once, so that the injector can resolve the dependencies.

        Example:

        >>> def foo(injector: Dependencies = Dependencies.Provides(int, str)):
        ...     injector.set(int, 42)
        ...     injector.set(str, "Hello, world!")
        ...
        >>> injector = Dependencies()
        >>> foo = injector.bind(foo)
        >>> injector.get(int)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        Dependencies.Error: unable to provide a dependency for type int, but the type was declared
        >>> foo()
        >>> injector.get(int)
        42
        """

        return Dependencies._Provides(list(types))

    def fork(self) -> Dependencies:
        """
        Create a new injector that inherits the bindings of this injector.

        >>> a = Dependencies()
        >>> a.set(int, 42)
        >>> b = a.fork()
        >>> b.set(str, "Hello, world!")
        >>> a.get(int)
        42
        >>> b.get(int)
        42
        >>> a.get(str)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        Dependencies.Error: unable to provide a dependency for type str
        >>> b.get(str)
        'Hello, world!'
        """

        return Dependencies(parent=self)


@deprecated(reason="use Dependencies.Provides() instead", version="0.0.8")
def DelayedBinding(*types: Type[Any]) -> Any:
    """
    Deprecated. Use #Dependencies.Provides() instead.
    """

    return Dependencies.Provides(*types)


@deprecated(reason="use Dependencies instead", version="0.0.8")
class DependencyInjector(Dependencies):
    """
    Deprecated. Use #Dependencies instead.
    """


# Deprecated, use Dependencies.Error instead.
DependencyInjectionError = Dependencies.Error
