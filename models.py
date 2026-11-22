"""Data models for the Notice Board Organizer.

Defines the Notice dataclass and category/status constants used across the
application. Keeping the record shape in one place makes persistence,
validation, and reporting consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Dict

# Allowed notice categories and their display labels.
CATEGORIES = (
    " academics ",
    "events",
    "administration",
    "maintenance",
    "sports",
    "deadlines",
    "general",
)
# Normalise (strip whitespace) for the valid set.
VALID_CATEGORIES = tuple(c.strip() for c in CATEGORIES)

# Expiry states a notice can be in.
ACTIVE = "Active"
EXPIRED = "Expired"
UPCOMING = "Upcoming"
VALID_STATUSES = (ACTIVE, EXPIRED, UPCOMING)

DATE_FORMAT = "%Y-%m-%d"


def compute_status(expiry: date, today: date | None = None) -> str:
    """Derive the expiry status from a date relative to today."""
    today = today or date.today()
    if expiry < today:
        return EXPIRED
    if expiry == today:
        return ACTIVE
    return UPCOMING


@dataclass
class Notice:
    """A single notice-board record."""

    id: int
    title: str
    category: str
    date_posted: date
    expiry_date: date
    status: str = ACTIVE
    author: str = "Admin"
    description: str = ""

    def days_remaining(self, today: date | None = None) -> int:
        """Return whole days until expiry (negative if overdue)."""
        today = today or date.today()
        return (self.expiry_date - today).days

    def is_overdue(self, today: date | None = None) -> bool:
        return self.days_remaining(today) < 0

    def refresh_status(self, today: date | None = None) -> None:
        """Recalculate status from the expiry date."""
        self.status = compute_status(self.expiry_date, today)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON/CSV friendly dictionary (dates as strings)."""
        data = asdict(self)
        data["date_posted"] = self.date_posted.strftime(DATE_FORMAT)
        data["expiry_date"] = self.expiry_date.strftime(DATE_FORMAT)
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Notice":
        """Build a Notice from a dictionary, parsing date strings."""
        posted = _parse_date(data["date_posted"])
        expiry = _parse_date(data["expiry_date"])
        notice = Notice(
            id=int(data["id"]),
            title=str(data["title"]),
            category=str(data["category"]),
            date_posted=posted,
            expiry_date=expiry,
            status=str(data.get("status") or compute_status(expiry)),
            author=str(data.get("author") or "Admin"),
            description=str(data.get("description") or ""),
        )
        notice.refresh_status()
        return notice


def _parse_date(value: Any) -> date:
    """Parse a date from a date object or an ISO date string."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), DATE_FORMAT).date()
        except ValueError:
            pass
        # Fall back to a forgiving ISO parse.
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError as exc:
            raise ValueError(f"Invalid date value: {value!r}") from exc
    raise ValueError(f"Invalid date value: {value!r}")
