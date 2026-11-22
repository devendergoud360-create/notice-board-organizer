"""Pure input validators (domain layer, no I/O).

Each validator raises ValidationError on failure and returns a normalised
value on success. These are the single source of truth for input rules, used
by the console wrappers, the import pipeline, and the API layer.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from domain.entities import VALID_CATEGORIES, DATE_FORMAT


class ValidationError(ValueError):
    """Raised when a value fails a domain validation rule."""


def validate_text(value: Any, field: str, min_len: int = 1, max_len: int = 120) -> str:
    text = (value or "").strip()
    if len(text) < min_len:
        raise ValidationError(f"{field} must not be empty.")
    if len(text) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    return text.strip()


def validate_category(value: Any) -> str:
    cat = str(value or "").strip().lower()
    if cat not in VALID_CATEGORIES:
        raise ValidationError(
            f"Unknown category {value!r}. Choose from: {', '.join(VALID_CATEGORIES)}"
        )
    return cat


def validate_date(value: Any, field: str = "date") -> date:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as exc:
        raise ValidationError(
            f"{field} must be a valid date in YYYY-MM-DD format (got {value!r})."
        ) from exc


def validate_positive_int(value: Any, field: str) -> int:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d+", text):
        raise ValidationError(f"{field} must be a positive whole number.")
    number = int(text)
    if number <= 0:
        raise ValidationError(f"{field} must be greater than zero.")
    return number


def validate_date_range(posted: date, expiry: date) -> None:
    if expiry < posted:
        raise ValidationError("Expiry date cannot be earlier than the date posted.")
