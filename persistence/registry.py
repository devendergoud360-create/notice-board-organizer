"""Backend registry (Strategy selection by name)."""

from __future__ import annotations

from typing import Callable, Dict, List

from .base import StorageBackend

_REGISTRY: Dict[str, Callable[..., StorageBackend]] = {}


def register_backend(name: str, factory: Callable[..., StorageBackend]) -> None:
    key = name.lower()
    if key in _REGISTRY:
        raise ValueError(f"backend already registered: {name}")
    _REGISTRY[key] = factory


def get_backend(name: str, *args, **kwargs) -> StorageBackend:
    key = name.lower()
    if key not in _REGISTRY:
        raise KeyError(f"unknown storage backend: {name!r}. "
                       f"Available: {', '.join(sorted(_REGISTRY))}")
    return _REGISTRY[key](*args, **kwargs)


def available_backends() -> List[str]:
    return sorted(_REGISTRY)
