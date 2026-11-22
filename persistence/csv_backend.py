"""CSV storage backend with atomic writes and row-level validation."""

from __future__ import annotations

import csv
import os
from typing import List

from domain import Notice
from .base import StorageBackend, CSV_FIELDS  # shared field list


class CsvBackend(StorageBackend):
    name = "csv"

    def __init__(self, path: str):
        self.path = path

    def location(self) -> str:
        return self.path

    def _emit(self, event: str, data: dict) -> None:
        try:
            from application.events import bus
            bus.emit(event, data)
        except Exception:
            pass

    def load(self) -> List[Notice]:
        if not os.path.exists(self.path):
            return []
        notices = []
        try:
            with open(self.path, "r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    try:
                        n = Notice.from_dict(dict(row))
                        n.validate()
                        notices.append(n)
                    except (ValueError, KeyError, TypeError) as exc:
                        self._emit("storage.skipped_row",
                                   {"row": row.get("id"), "error": str(exc)})
        except OSError as exc:
            self._emit("storage.load_failed", {"error": str(exc)})
        return notices

    def save(self, notices: List[Notice]) -> bool:
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            temp = self.path + ".tmp"
            with open(temp, "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
                writer.writeheader()
                for n in notices:
                    writer.writerow(n.to_dict())
            os.replace(temp, self.path)
            self._emit("storage.saved", {"backend": "csv", "count": len(notices)})
            return True
        except OSError as exc:
            self._emit("storage.save_failed", {"error": str(exc)})
            return False
