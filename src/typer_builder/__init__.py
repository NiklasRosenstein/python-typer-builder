__version__ = "0.0.10"

from .build_app import build_app_from_module
from .Dependencies import DelayedBinding, Dependencies, DependencyInjectionError, DependencyInjector

__all__ = [
    "build_app_from_module",
    "Dependencies",
    "DependencyInjectionError",
    # Deprecated
    "DelayedBinding",
    "DependencyInjector",
]
