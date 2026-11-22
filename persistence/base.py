"""Storage backend interface (Strategy pattern)."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Callable, List

from domain import Notice

CSV_FIELDS = [
    "id", "title", "category", "date_posted", "expiry_date",
    "status", "author", "description",
]


def atomic_write(path: str, writer: Callable[[str], None], retries: int = 3) -> bool:
    """Write via temp file + os.replace, with retries for transient OS locks.

    Windows can briefly hold a handle on a file being replaced; retrying makes
    persistence deterministic under concurrent access (CI, browser QA, API).
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp = f"{path}.tmp"
    for attempt in range(retries):
        try:
            writer(temp)
            os.replace(temp, path)
            return True
        except OSError:
            try:
                if os.path.exists(temp):
                    os.remove(temp)
            except OSError:
                pass
            if attempt < retries - 1:
                time.sleep(0.05 * (attempt + 1))
    return False


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
