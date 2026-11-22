"""Console input wrappers (presentation layer).

Loop until the user supplies a value accepted by the domain validators, so
blank / malformed / non-numeric / out-of-range input never crashes the app.
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Optional

from domain.entities import VALID_CATEGORIES, DATE_FORMAT
from domain.validation import (
    ValidationError, validate_text, validate_category, validate_date,
    validate_positive_int,
)


def prompt_until_valid(
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
    helper = f" (default: {default})" if default else ""
    return str(prompt_until_valid(
        prompt + helper + ": ", lambda v: validate_text(v, field)))


def ask_category(prompt: str = "Category") -> str:
    print("  Categories: " + ", ".join(VALID_CATEGORIES))
    return str(prompt_until_valid(prompt + ": ", validate_category))


def ask_date(prompt: str, field: str = "date", default: Optional[date] = None) -> date:
    helper = f" (default: {default.strftime(DATE_FORMAT)})" if default else ""
    parser = lambda v: default if (not v and default) else validate_date(v, field)
    return prompt_until_valid(prompt + helper + f" [{DATE_FORMAT}]: ", parser)


def ask_positive_int(prompt: str) -> int:
    return int(prompt_until_valid(
        prompt + ": ", lambda v: validate_positive_int(v, prompt)))


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
