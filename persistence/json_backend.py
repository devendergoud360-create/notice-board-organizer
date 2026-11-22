"""JSON storage backend with atomic writes and corrupt-file backup/recovery."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from typing import List

from domain import Notice
from .base import StorageBackend


class JsonBackend(StorageBackend):
    name = "json"

    def __init__(self, path: str):
        self.path = path

    def location(self) -> str:
        return self.path

    def _backup_corrupt(self, reason: str) -> None:
        if not os.path.exists(self.path):
            return
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = f"{self.path}.corrupt.{stamp}.bak"
        try:
            shutil.copy2(self.path, backup)
        except OSError:
            return
        self._emit("storage.corrupt_backup", {"backup": backup, "reason": reason})

    def _emit(self, event: str, data: dict) -> None:
        try:
            from application.events import bus
            bus.emit(event, data)
        except Exception:
            pass

    def load(self) -> List[Notice]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
            if not content:
                return []
            records = json.loads(content)
            if not isinstance(records, list):
                raise ValueError("JSON root must be a list")
            notices = []
            for rec in records:
                try:
                    n = Notice.from_dict(rec)
                    n.validate()
                    notices.append(n)
                except (ValueError, KeyError, TypeError) as exc:
                    self._emit("storage.skipped_record", {"error": str(exc)})
            return notices
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            self._backup_corrupt(str(exc))
            self._emit("storage.load_failed", {"error": str(exc)})
            return []

    def save(self, notices: List[Notice]) -> bool:
        def _write(temp: str) -> None:
            with open(temp, "w", encoding="utf-8") as fh:
                json.dump([n.to_dict() for n in notices], fh,
                          indent=2, ensure_ascii=False)

        from .base import atomic_write
        ok = atomic_write(self.path, _write)
        if ok:
            self._emit("storage.saved", {"backend": "json", "count": len(notices)})
        else:
            self._emit("storage.save_failed", {"backend": "json"})
        return ok
