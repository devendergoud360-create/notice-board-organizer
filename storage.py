"""Local persistence for the Notice Board Organizer (JSON + CSV).

All file access is wrapped in try/except so corrupted, missing, or empty
storage files never crash the application.
"""

from __future__ import annotations

import csv
import json
import os
from typing import List

from models import Notice

CSV_FIELDS = [
    "id",
    "title",
    "category",
    "date_posted",
    "expiry_date",
    "status",
    "author",
    "description",
]


def ensure_storage(directory: str) -> None:
    """Create the data directory if it does not exist."""
    os.makedirs(directory, exist_ok=True)


def load_json(path: str) -> List[Notice]:
    """Load notices from JSON. Returns [] on missing/corrupt files."""
    ensure_storage(os.path.dirname(path) or ".")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read().strip()
            if not content:
                return []
            records = json.loads(content)
        notices = []
        for rec in records:
            try:
                notices.append(Notice.from_dict(rec))
            except (ValueError, KeyError, TypeError) as exc:
                print(f"  [!] Skipping invalid record in {path}: {exc}")
        return notices
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [!] Could not read {path}: {exc}. Starting with empty store.")
        return []


def save_json(path: str, notices: List[Notice]) -> bool:
    """Atomically write notices to JSON. Returns True on success."""
    try:
        ensure_storage(os.path.dirname(path) or ".")
        temp = path + ".tmp"
        with open(temp, "w", encoding="utf-8") as fh:
            json.dump([n.to_dict() for n in notices], fh, indent=2, ensure_ascii=False)
        os.replace(temp, path)
        return True
    except OSError as exc:
        print(f"  [!] Failed to save JSON: {exc}")
        return False


def load_csv(path: str) -> List[Notice]:
    """Load notices from CSV (used for bulk import)."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    notices = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            notices.append(Notice.from_dict(dict(row)))
    return notices


def save_csv(path: str, notices: List[Notice]) -> bool:
    """Write all notices to a CSV file."""
    try:
        ensure_storage(os.path.dirname(path) or ".")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for n in notices:
                writer.writerow(n.to_dict())
        return True
    except OSError as exc:
        print(f"  [!] Failed to save CSV: {exc}")
        return False
