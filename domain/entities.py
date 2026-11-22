"""Domain entities - pure data and business rules, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict

VALID_CATEGORIES = (
    "academics", "events", "administration", "maintenance",
    "sports", "deadlines", "general",
)
ACTIVE, EXPIRED, UPCOMING = "Active", "Expired", "Upcoming"
VALID_STATUSES = (ACTIVE, EXPIRED, UPCOMING)
DATE_FORMAT = "%Y-%m-%d"


def compute_status(expiry: date, today: date | None = None) -> str:
    """Derive expiry status from a date relative to today."""
    today = today or date.today()
    if expiry < today:
        return EXPIRED
    if expiry == today:
        return ACTIVE
    return UPCOMING


def parse_date(value: Any) -> date:
    """Parse a date from a date/datetime object or ISO date string."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return datetime.strptime(text, DATE_FORMAT).date()
        except ValueError:
            pass
        try:
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError(f"Invalid date value: {value!r}") from exc
    raise ValueError(f"Invalid date value: {value!r}")


@dataclass
class Notice:
    """A single notice-board record (pure domain object)."""

    id: int
    title: str
    category: str
    date_posted: date
    expiry_date: date
    status: str = ACTIVE
    author: str = "Admin"
    description: str = ""

    def days_remaining(self, today: date | None = None) -> int:
        today = today or date.today()
        return (self.expiry_date - today).days

    def is_overdue(self, today: date | None = None) -> bool:
        return self.days_remaining(today) < 0

    def refresh_status(self, today: date | None = None) -> None:
        self.status = compute_status(self.expiry_date, today)

    def validate(self) -> None:
        """Enforce domain invariants. Raises ValueError on violation."""
        if self.id <= 0:
            raise ValueError("id must be positive")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"invalid category: {self.category!r}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {self.status!r}")
        if self.expiry_date < self.date_posted:
            raise ValueError("expiry_date cannot precede date_posted")
        if len(self.title) > 120 or len(self.description) > 2000:
            raise ValueError("text field exceeds maximum length")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "date_posted": self.date_posted.strftime(DATE_FORMAT),
            "expiry_date": self.expiry_date.strftime(DATE_FORMAT),
            "status": self.status,
            "author": self.author,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Notice":
        expiry = parse_date(data["expiry_date"])
        posted = parse_date(data["date_posted"])
        notice = Notice(
            id=int(data["id"]),
            title=str(data["title"]),
            category=str(data["category"]).lower(),
            date_posted=posted,
            expiry_date=expiry,
            status=str(data.get("status") or compute_status(expiry)),
            author=str(data.get("author") or "Admin"),
            description=str(data.get("description") or ""),
        )
        notice.refresh_status()
        return notice
