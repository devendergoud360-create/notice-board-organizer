"""Application service facade: orchestrates domain, persistence, and events."""

from __future__ import annotations

import os
from datetime import date
from typing import Dict, List

import persistence.bootstrap  # noqa: F401 - registers backends
from domain import Notice, NoticeService
from persistence import get_backend

from .events import FileSink, bus


class App:
    """Use-case facade shared by CLI and HTTP presentation layers."""

    def __init__(self, backend: str = "json", path: str | None = None,
                 log_path: str | None = None, today: date | None = None):
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        if path is None:
            ext = {"json": "notices.json", "csv": "notices.csv",
                   "sqlite": "notices.db"}.get(backend.lower(), "notices.json")
            path = os.path.join(base, ext)
        self.backend_name = backend
        self.backend = get_backend(backend, path)
        self.today = today or date.today()
        self.notices: List[Notice] = []
        if log_path:
            bus.subscribe("*", FileSink(log_path))
        bus.emit("app.initialized", {"backend": backend, "path": path})
        self.load()

    # ---- persistence ----
    def load(self) -> None:
        self.notices = self.backend.load()
        NoticeService.refresh_all(self.notices, self.today)
        bus.emit("app.loaded", {"count": len(self.notices)})

    def save(self) -> bool:
        ok = self.backend.save(self.notices)
        bus.emit("app.saved", {"backend": self.backend_name, "ok": ok})
        return ok

    # ---- commands ----
    def add(self, **fields) -> Notice:
        notice = Notice(
            id=NoticeService.next_id(self.notices),
            title=fields["title"], category=fields["category"],
            date_posted=fields["date_posted"], expiry_date=fields["expiry_date"],
            status="Active", author=fields.get("author", "Admin"),
            description=fields.get("description", ""),
        )
        created = NoticeService.add(self.notices, notice)
        created.refresh_status(self.today)
        self.save()
        bus.emit("notice.added", {"id": created.id, "title": created.title})
        return created

    def update(self, notice_id: int, **changes) -> Notice | None:
        updated = NoticeService.update(self.notices, notice_id, **changes)
        if updated:
            updated.refresh_status(self.today)
            self.save()
            bus.emit("notice.updated", {"id": notice_id})
        return updated

    def delete(self, notice_id: int) -> bool:
        ok = NoticeService.delete(self.notices, notice_id)
        if ok:
            self.save()
            bus.emit("notice.deleted", {"id": notice_id})
        return ok

    def get(self, notice_id: int) -> Notice | None:
        return NoticeService.get(self.notices, notice_id)

    def search(self, keyword: str = "", category: str = "") -> List[Notice]:
        return NoticeService.search(self.notices, keyword, category)

    def summary(self) -> Dict[str, object]:
        return NoticeService.summary(self.notices, self.today)

    def warnings(self) -> List[dict]:
        return NoticeService.warnings(self.notices, self.today)

    def risk(self, notice_id: int):
        return NoticeService.risk(self.notices, notice_id, self.today)

    def ranked(self) -> List[dict]:
        return NoticeService.ranked(self.notices, self.today)

    def replace_all(self, notices: List[Notice]) -> None:
        self.notices = notices
        NoticeService.refresh_all(self.notices, self.today)
        self.save()
        bus.emit("app.replaced", {"count": len(notices)})

    def import_rows(self, rows: List[dict], replace: bool = False) -> dict:
        """Row-level validated bulk import. Returns {added, skipped, errors}."""
        imported: List[Notice] = []
        errors = []
        for row in rows:
            try:
                n = Notice.from_dict(row)
                n.validate()
                imported.append(n)
            except (ValueError, KeyError, TypeError) as exc:
                errors.append({"row": row.get("id"), "error": str(exc)})
                bus.emit("import.row_rejected", {"error": str(exc)})
        if replace:
            target: List[Notice] = []
        else:
            target = list(self.notices)
        for n in imported:
            n.id = NoticeService.next_id(target)
            n.refresh_status(self.today)
            target.append(n)
        self.replace_all(target)
        result = {"added": len(imported), "skipped": len(errors), "errors": errors}
        bus.emit("import.completed", result)
        return result
