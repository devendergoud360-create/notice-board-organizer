"""Core business logic for the Notice Board Organizer.

Pure functions that operate on a list of Notice objects. Keeping these
separate from UI and storage makes them easy to test and reuse.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

from models import Notice, ACTIVE, EXPIRED, UPCOMING


def next_id(notices: List[Notice]) -> int:
    """Return the next available integer id."""
    return max((n.id for n in notices), default=0) + 1


def refresh_all(notices: List[Notice]) -> None:
    """Recompute expiry status for every notice."""
    for n in notices:
        n.refresh_status()


def add_notice(notices: List[Notice], notice: Notice) -> None:
    notices.append(notice)
    refresh_all(notices)


def delete_notice(notices: List[Notice], notice_id: int) -> bool:
    """Delete by id. Returns True if a record was removed."""
    before = len(notices)
    notices[:] = [n for n in notices if n.id != notice_id]
    return len(notices) < before


def find_by_id(notices: List[Notice], notice_id: int) -> Notice | None:
    return next((n for n in notices if n.id == notice_id), None)


def search(
    notices: List[Notice],
    keyword: str = "",
    category: str = "",
) -> List[Notice]:
    """Filter by keyword (title/description/author) and/or category."""
    kw = keyword.strip().lower()
    cat = category.strip().lower()
    results = []
    for n in notices:
        if cat and n.category.lower() != cat:
            continue
        if kw:
            haystack = f"{n.title} {n.description} {n.author}".lower()
            if kw not in haystack:
                continue
        results.append(n)
    return results


def summary(notices: List[Notice]) -> Dict[str, object]:
    """Compute headline metrics for the executive summary."""
    refresh_all(notices)
    total = len(notices)
    status_counts = Counter(n.status for n in notices)
    category_counts = Counter(n.category for n in notices)
    overdue = sum(1 for n in notices if n.is_overdue())
    expiring_soon = sum(1 for n in notices if 0 <= n.days_remaining() <= 7)
    days = [n.days_remaining() for n in notices]
    avg_days = round(sum(days) / total, 1) if total else 0.0
    return {
        "total": total,
        "active": status_counts.get(ACTIVE, 0),
        "upcoming": status_counts.get(UPCOMING, 0),
        "expired": status_counts.get(EXPIRED, 0),
        "overdue": overdue,
        "expiring_soon": expiring_soon,
        "avg_days_remaining": avg_days,
        "category_counts": dict(category_counts.most_common()),
    }


def warnings(notices: List[Notice]) -> List[Tuple[Notice, str]]:
    """Return (notice, message) pairs for threshold warnings."""
    refresh_all(notices)
    out: List[Tuple[Notice, str]] = []
    for n in notices:
        remaining = n.days_remaining()
        if remaining < 0:
            out.append((n, f"OVERDUE by {abs(remaining)} day(s)"))
        elif remaining <= 3:
            out.append((n, f"Expires in {remaining} day(s)"))
    return out


def sort_notices(notices: List[Notice], key: str = "expiry") -> List[Notice]:
    """Return a sorted copy. key: id|title|category|posted|expiry|status."""
    mapping = {
        "id": lambda n: n.id,
        "title": lambda n: n.title.lower(),
        "category": lambda n: n.category,
        "posted": lambda n: n.date_posted,
        "expiry": lambda n: n.expiry_date,
        "status": lambda n: n.status,
    }
    return sorted(notices, key=mapping.get(key, mapping["expiry"]))
