"""Persistence layer - Strategy backends behind one interface + registry."""

from .base import StorageBackend
from .registry import get_backend, register_backend, available_backends

__all__ = ["StorageBackend", "get_backend", "register_backend", "available_backends"]
