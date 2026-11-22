"""Defensive input validation helpers.

Every user-supplied value passes through here before it reaches the business
logic. Functions loop until the user provides acceptable input so that the
main program never has to worry about malformed data.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional

from models import VALID_CATEGORIES, DATE_FORMAT, compute_status


class ValidationError(ValueError):
    """Raised when a value fails validation (used in bulk import)."""


# ---------------------------------------------------------------------------
# Pure validators (raise ValidationError). Reused by interactive and import.
# ---------------------------------------------------------------------------
def validate_text(value: str, field: str, min_len: int = 1, max_len: int = 120) -> str:
    text = (value or "").strip()
    if len(text) < min_len:
        raise ValidationError(f"{field} must not be empty.")
    if len(text) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    # Reject control characters (tab/newline collapse to space).
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    return text.strip()


def validate_category(value: str) -> str:
    cat = (value or "").strip().lower()
    if cat not in VALID_CATEGORIES:
        raise ValidationError(
            f"Unknown category {value!r}. Choose from: {', '.join(VALID_CATEGORIES)}"
        )
    return cat


def validate_date(value: str, field: str = "date") -> date:
    text = (value or "").strip()
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as exc:
        raise ValidationError(
            f"{field} must be a valid date in YYYY-MM-DD format (got {value!r})."
        ) from exc


def validate_positive_int(value: str, field: str) -> int:
    text = (value or "").strip()
    if not re.fullmatch(r"\d+", text):
        raise ValidationError(f"{field} must be a positive whole number.")
    number = int(text)
    if number <= 0:
        raise ValidationError(f"{field} must be greater than zero.")
    return number


def validate_date_range(posted: date, expiry: date) -> None:
    if expiry < posted:
        raise ValidationError(
            "Expiry date cannot be earlier than the date posted."
        )


# ---------------------------------------------------------------------------
# Interactive wrappers (loop until valid).
# ---------------------------------------------------------------------------
def _prompt_until_valid(
    prompt: str,
    parser: Callable[[str], object],
    default: Optional[object] = None,
) -> object:
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            return parser(raw)
        except ValidationError as exc:
            print(f"  [!] {exc} Please try again.")


def ask_text(prompt: str, field: str, default: Optional[str] = None) -> str:
    helper = (f" (default: {default})" if default else "")
    return str(
        _prompt_until_valid(
            prompt + helper + ": ",
            lambda v: validate_text(v, field),
        )
    )


def ask_category(prompt: str = "Category") -> str:
    print("  Categories: " + ", ".join(VALID_CATEGORIES))
    return str(_prompt_until_valid(prompt + ": ", validate_category))


def ask_date(prompt: str, field: str = "date", default: Optional[date] = None) -> date:
    helper = f" (default: {default.strftime(DATE_FORMAT)})" if default else ""
    parser = lambda v: default if (not v and default) else validate_date(v, field)
    return _prompt_until_valid(prompt + helper + f" [{DATE_FORMAT}]: ", parser)


def ask_positive_int(prompt: str) -> int:
    return int(_prompt_until_valid(prompt + ": ", lambda v: validate_positive_int(v, prompt)))


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = " [y/N]: " if not default else " [Y/n]: "
    while True:
        raw = input(prompt + suffix).strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  [!] Please type 'y' or 'n'.")
