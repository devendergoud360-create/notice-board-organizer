"""Pure domain layer - no I/O, no framework, no UI."""

from .entities import (
    Notice, VALID_CATEGORIES, VALID_STATUSES,
    ACTIVE, EXPIRED, UPCOMING, compute_status,
)
from .services import NoticeService

__all__ = [
    "Notice", "VALID_CATEGORIES", "VALID_STATUSES",
    "ACTIVE", "EXPIRED", "UPCOMING", "compute_status", "NoticeService",
]
