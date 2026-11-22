"""Storage backend interface (Strategy pattern)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from domain import Notice

CSV_FIELDS = [
    "id", "title", "category", "date_posted", "expiry_date",
    "status", "author", "description",
]


class StorageBackend(ABC):
    """Strategy interface: every backend load/saves a full notice collection."""

    name: str = "base"

    @abstractmethod
    def load(self) -> List[Notice]:
        """Load all records. Missing/corrupt data yields [] after recovery."""

    @abstractmethod
    def save(self, notices: List[Notice]) -> bool:
        """Atomically persist all records. Returns True on success."""

    # Optional hook backends may override to report a human-readable location.
    def location(self) -> str:
        return self.name
