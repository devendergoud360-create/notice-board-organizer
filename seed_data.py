"""Generate realistic sample datasets (30-50 entries) in CSV and JSON.

Run: python seed_data.py
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date, timedelta
from random import Random

from domain import Notice, compute_status
from persistence.base import CSV_FIELDS

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

TITLES = [
    "Midterm Examination Schedule", "Library Maintenance", "Career Fair 2026",
    "Scholarship Application Deadline", "Campus Clean-Up Drive", "Guest Lecture: AI",
    "Sports Meet Registration", "Hostel Inspection", "Tuition Fee Submission",
    "Research Grant Call", "Alumni Networking Night", "Water Supply Interruption",
    "Course Enrollment Opens", "Annual Report Submission", "Internship Postings",
    "Safety Drill", "Cultural Festival", "Thesis Proposal Deadline",
    "Wi-Fi Upgrade", "Counseling Services", "Hackathon 2026", "Exam Results Release",
    "New Club Registration", "Parking Permit Renewal", "Health Checkup Camp",
    "Seminar on Cybersecurity", "Budget Approval Meeting", "Lost & Found Notice",
    "Graduation Rehearsal", "Lab Equipment Upgrade",
]
CATEGORIES = [
    "academics", "events", "administration", "maintenance",
    "sports", "deadlines", "general",
]
AUTHORS = ["Admin", "Registrar", "Student Affairs", "IT Department", "Faculty Club"]


def generate(count: int = 40, seed: int = 42) -> list[Notice]:
    rng = Random(seed)
    today = date.today()
    notices = []
    for i in range(1, count + 1):
        posted = today - timedelta(days=rng.randint(1, 60))
        offset = rng.randint(-20, 45)  # negative => overdue
        expiry = today + timedelta(days=offset)
        notice = Notice(
            id=i,
            title=TITLES[(i - 1) % len(TITLES)],
            category=CATEGORIES[rng.randrange(len(CATEGORIES))],
            date_posted=posted,
            expiry_date=expiry,
            status=compute_status(expiry, today),
            author=AUTHORS[rng.randrange(len(AUTHORS))],
            description=f"Sample notice #{i} generated for the hackathon demo.",
        )
        if expiry < posted:  # keep a few deliberate edge-case mismatches valid
            notice.expiry_date = notice.date_posted + timedelta(days=1)
            notice.refresh_status(today)
        notices.append(notice)
    return notices


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    notices = generate()

    json_path = os.path.join(DATA_DIR, "sample_notices.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump([n.to_dict() for n in notices], fh, indent=2, ensure_ascii=False)

    csv_path = os.path.join(DATA_DIR, "sample_notices.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for n in notices:
            writer.writerow(n.to_dict())

    print(f"Wrote {len(notices)} sample records:")
    print(f"  {json_path}")
    print(f"  {csv_path}")


if __name__ == "__main__":
    main()
