"""Reporting and export presenters (presentation layer).

Builds terminal tables and exports Markdown/plain-text/CSV. Uses the pure
domain service for summaries and warnings; emits structured events instead of
operational print() calls.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, List, Sequence

from domain import Notice, NoticeService
from persistence.base import CSV_FIELDS


def _emit(event: str, data: dict) -> None:
    try:
        from application.events import bus
        bus.emit(event, data)
    except Exception:
        pass


def format_table(notices: Sequence[Notice], page_size: int = 12) -> str:
    """Fixed-width, paginated table text for terminal display."""
    if not notices:
        return "  (no records to display)"
    headers = ["ID", "Title", "Category", "Posted", "Expires", "Days", "Status"]
    rows = [[
        str(n.id), _truncate(n.title, 28), _truncate(n.category, 13),
        n.date_posted.strftime("%Y-%m-%d"), n.expiry_date.strftime("%Y-%m-%d"),
        str(n.days_remaining()), n.status,
    ] for n in notices]
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))]
    line = "+ " + " + ".join("-" * w for w in widths) + " +"
    out = [line, " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)), line]
    for idx, row in enumerate(rows, start=1):
        out.append(" | ".join(row[i].ljust(widths[i]) for i in range(len(row))))
        if idx % page_size == 0 and idx < len(rows):
            out.append(f"  ... page break ({idx}/{len(rows)}) ...")
    out += [line, f"  {len(notices)} record(s) shown."]
    return "\n".join(out)


def format_summary(s: Dict[str, object]) -> str:
    lines = [
        "  EXECUTIVE SUMMARY", "  " + "-" * 40,
        f"  Total notices ............ {s['total']}",
        f"  Active ................... {s['active']}",
        f"  Upcoming ................. {s['upcoming']}",
        f"  Expired .................. {s['expired']}",
        f"  Overdue .................. {s['overdue']}",
        f"  Expiring within 7 days ... {s['expiring_soon']}",
        f"  Avg days remaining ....... {s['avg_days_remaining']}",
    ]
    cats = s["category_counts"] or {}
    if cats:
        lines.append("  By category:")
        lines += [f"    - {cat:<15} {count}" for cat, count in cats.items()]
    return "\n".join(lines)


def export_markdown(path: str, notices: List[Notice]) -> bool:
    s = NoticeService.summary(notices)
    lines = [
        "# Notice Board Organizer — Report", "",
        f"Generated: {_now()}", "", "## Executive Summary", "",
        f"- **Total notices:** {s['total']}",
        f"- **Active:** {s['active']}",
        f"- **Upcoming:** {s['upcoming']}",
        f"- **Expired:** {s['expired']}",
        f"- **Overdue:** {s['overdue']}",
        f"- **Expiring within 7 days:** {s['expiring_soon']}",
        f"- **Avg days remaining:** {s['avg_days_remaining']}", "",
        "## Notices", "",
        "| ID | Title | Category | Posted | Expires | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {n.id} | {n.title} | {n.category} | {n.date_posted} | "
        f"{n.expiry_date} | {n.status} |" for n in notices
    ]
    warns = NoticeService.warnings(notices)
    if warns:
        lines += ["", "## Warnings", ""]
        lines += [f"- #{w['id']} {w['title']}: {w['message']}" for w in warns]
    ok = _write(path, "\n".join(lines) + "\n")
    _emit("export.markdown", {"path": path, "records": len(notices), "ok": ok})
    return ok


def export_text(path: str, notices: List[Notice]) -> bool:
    lines = [
        "NOTICE BOARD ORGANIZER - AUDIT LOG", f"Generated: {_now()}",
        "=" * 60, format_summary(NoticeService.summary(notices)), "=" * 60,
        format_table(notices, page_size=10**9),
    ]
    warns = NoticeService.warnings(notices)
    if warns:
        lines.append("\nWARNINGS:")
        lines += [f"  #{w['id']} {w['title']}: {w['message']}" for w in warns]
    ok = _write(path, "\n".join(lines) + "\n")
    _emit("export.text", {"path": path, "records": len(notices), "ok": ok})
    return ok


def export_csv(path: str, notices: List[Notice]) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for n in notices:
                writer.writerow(n.to_dict())
        _emit("export.csv", {"path": path, "records": len(notices), "ok": True})
        return True
    except OSError as exc:
        _emit("export.failed", {"path": path, "error": str(exc)})
        return False


def _write(path: str, content: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return True
    except OSError as exc:
        _emit("export.failed", {"path": path, "error": str(exc)})
        return False


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
