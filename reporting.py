"""Report export and tabular display helpers."""

from __future__ import annotations

import csv
import os
from typing import Dict, List

from logic import summary, warnings
from models import Notice
from storage import CSV_FIELDS


# ---------------------------------------------------------------------------
# Console tables
# ---------------------------------------------------------------------------
def format_table(notices: List[Notice], page_size: int = 12) -> str:
    """Build fixed-width, paginated table text for terminal display."""
    if not notices:
        return "  (no records to display)"

    headers = ["ID", "Title", "Category", "Posted", "Expires", "Days", "Status"]
    rows = []
    for n in notices:
        rows.append([
            str(n.id),
            _truncate(n.title, 28),
            _truncate(n.category, 13),
            n.date_posted.strftime("%Y-%m-%d"),
            n.expiry_date.strftime("%Y-%m-%d"),
            str(n.days_remaining()),
            n.status,
        ])
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))]
    line = "+ " + " + ".join("-" * w for w in widths) + " +"

    out = [line, " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)), line]
    for idx, row in enumerate(rows, start=1):
        out.append(" | ".join(row[i].ljust(widths[i]) for i in range(len(row))))
        if idx % page_size == 0 and idx < len(rows):
            out.append(f"  ... page break ({idx}/{len(rows)}) ...")
    out.append(line)
    out.append(f"  {len(notices)} record(s) shown.")
    return "\n".join(out)


def format_summary(s: Dict[str, object]) -> str:
    lines = [
        "  EXECUTIVE SUMMARY",
        "  " + "-" * 40,
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
        for cat, count in cats.items():
            lines.append(f"    - {cat:<15} {count}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File exports
# ---------------------------------------------------------------------------
def export_markdown(path: str, notices: List[Notice]) -> bool:
    s = summary(notices)
    lines = [
        "# Notice Board Organizer — Report",
        "",
        f"Generated: {_now()}",
        "",
        "## Executive Summary",
        "",
        f"- **Total notices:** {s['total']}",
        f"- **Active:** {s['active']}",
        f"- **Upcoming:** {s['upcoming']}",
        f"- **Expired:** {s['expired']}",
        f"- **Overdue:** {s['overdue']}",
        f"- **Expiring within 7 days:** {s['expiring_soon']}",
        f"- **Avg days remaining:** {s['avg_days_remaining']}",
        "",
        "## Notices",
        "",
        "| ID | Title | Category | Posted | Expires | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for n in notices:
        lines.append(
            f"| {n.id} | {n.title} | {n.category} | "
            f"{n.date_posted} | {n.expiry_date} | {n.status} |"
        )
    warns = warnings(notices)
    if warns:
        lines += ["", "## Warnings", ""]
        for n, msg in warns:
            lines.append(f"- #{n.id} {n.title}: {msg}")
    return _write(path, "\n".join(lines) + "\n")


def export_text(path: str, notices: List[Notice]) -> bool:
    lines = [
        "NOTICE BOARD ORGANIZER - AUDIT LOG",
        f"Generated: {_now()}",
        "=" * 60,
        format_summary(summary(notices)),
        "=" * 60,
        format_table(notices, page_size=10**9),
    ]
    warns = warnings(notices)
    if warns:
        lines.append("\nWARNINGS:")
        for n, msg in warns:
            lines.append(f"  #{n.id} {n.title}: {msg}")
    return _write(path, "\n".join(lines) + "\n")


def export_csv(path: str, notices: List[Notice]) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for n in notices:
                writer.writerow(n.to_dict())
        return True
    except OSError as exc:
        print(f"  [!] Export failed: {exc}")
        return False


def _write(path: str, content: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return True
    except OSError as exc:
        print(f"  [!] Export failed: {exc}")
        return False


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
