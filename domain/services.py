"""Domain services - pure operations on Notice collections."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Dict, List, Sequence, Tuple

from risk import compute_risk, risk_breakdown

from .entities import ACTIVE, EXPIRED, UPCOMING, Notice, compute_status


class NoticeService:
    """Stateless business engine operating on a supplied collection."""

    @staticmethod
    def next_id(notices: Sequence[Notice]) -> int:
        return max((n.id for n in notices), default=0) + 1

    @staticmethod
    def refresh_all(notices: List[Notice], today: date | None = None) -> None:
        for n in notices:
            n.refresh_status(today)

    @staticmethod
    def add(notices: List[Notice], notice: Notice) -> Notice:
        notice.id = NoticeService.next_id(notices)
        notice.refresh_status()
        notice.validate()
        notices.append(notice)
        return notice

    @staticmethod
    def update(notices: List[Notice], notice_id: int, **changes) -> Notice | None:
        target = NoticeService.get(notices, notice_id)
        if target is None:
            return None
        merged = target.to_dict()
        merged.update(changes)
        updated = Notice.from_dict(merged)
        # keep identity and validate whole entity
        updated.id = target.id
        updated.validate()
        idx = notices.index(target)
        notices[idx] = updated
        return updated

    @staticmethod
    def delete(notices: List[Notice], notice_id: int) -> bool:
        before = len(notices)
        notices[:] = [n for n in notices if n.id != notice_id]
        return len(notices) < before

    @staticmethod
    def get(notices: Sequence[Notice], notice_id: int) -> Notice | None:
        return next((n for n in notices if n.id == notice_id), None)

    @staticmethod
    def search(
        notices: Sequence[Notice], keyword: str = "", category: str = ""
    ) -> List[Notice]:
        kw, cat = keyword.strip().lower(), category.strip().lower()
        out = []
        for n in notices:
            if cat and n.category.lower() != cat:
                continue
            if kw and kw not in f"{n.title} {n.description} {n.author}".lower():
                continue
            out.append(n)
        return out

    @staticmethod
    def summary(notices: Sequence[Notice], today: date | None = None) -> Dict[str, object]:
        counts = Counter(n.status for n in notices)
        cats = Counter(n.category for n in notices)
        days = [n.days_remaining(today) for n in notices]
        overdue = sum(1 for n in notices if n.is_overdue(today))
        soon = sum(1 for d in days if 0 <= d <= 7)
        return {
            "total": len(notices),
            "active": counts.get(ACTIVE, 0),
            "upcoming": counts.get(UPCOMING, 0),
            "expired": counts.get(EXPIRED, 0),
            "overdue": overdue,
            "expiring_soon": soon,
            "avg_days_remaining": round(sum(days) / len(days), 1) if days else 0.0,
            "category_counts": dict(cats.most_common()),
        }

    @staticmethod
    def warnings(notices: Sequence[Notice], today: date | None = None) -> List[dict]:
        out = []
        for n in notices:
            remaining = n.days_remaining(today)
            if remaining < 0:
                out.append({"id": n.id, "title": n.title,
                            "message": f"OVERDUE by {abs(remaining)} day(s)"})
            elif remaining <= 3:
                out.append({"id": n.id, "title": n.title,
                            "message": f"Expires in {remaining} day(s)"})
        return out

    @staticmethod
    def sort(notices: Sequence[Notice], key: str = "expiry") -> List[Notice]:
        mapping = {
            "id": lambda n: n.id,
            "title": lambda n: n.title.lower(),
            "category": lambda n: n.category,
            "expiry": lambda n: n.expiry_date,
            "posted": lambda n: n.date_posted,
            "status": lambda n: n.status,
        }
        return sorted(notices, key=mapping.get(key, mapping["expiry"]))

    @staticmethod
    def risk(notices: Sequence[Notice], notice_id: int, today: date | None = None):
        target = NoticeService.get(notices, notice_id)
        if target is None:
            return None
        return risk_breakdown(target, notices, today)

    @staticmethod
    def ranked(notices: Sequence[Notice], today: date | None = None) -> List[dict]:
        return sorted(
            (
                {"id": n.id, "title": n.title,
                 "risk_score": compute_risk(n, notices, today)}
                for n in notices
            ),
            key=lambda r: r["risk_score"],
            reverse=True,
        )
