"""Smoke tests for the Notice Board Organizer (stdlib unittest).

Exercises domain validation, logic, persistence backends, and reporting.
"""

import os
import tempfile
import unittest
from datetime import date, timedelta

from domain import Notice, NoticeService, ACTIVE, EXPIRED, UPCOMING
from domain.validation import (
    ValidationError, validate_category, validate_date,
    validate_date_range, validate_text,
)
import persistence.bootstrap  # noqa: F401
from persistence import get_backend
from presentation import export_csv, export_markdown, export_text, format_table

TODAY = date.today()


def make_notice(nid, title, category="academics", offset=5, posted=None):
    expiry = TODAY + timedelta(days=offset)
    n = Notice(
        id=nid, title=title, category=category,
        date_posted=posted or (TODAY - timedelta(days=10)),
        expiry_date=expiry, status=ACTIVE,
    )
    n.refresh_status(TODAY)
    return n


class ValidationTests(unittest.TestCase):
    def test_text(self):
        self.assertEqual(validate_text("  Hello ", "title"), "Hello")
        with self.assertRaises(ValidationError):
            validate_text("   ", "title")

    def test_category(self):
        self.assertEqual(validate_category(" EVENTS "), "events")
        with self.assertRaises(ValidationError):
            validate_category("unknown")

    def test_date(self):
        self.assertEqual(validate_date("2026-01-15"), date(2026, 1, 15))
        with self.assertRaises(ValidationError):
            validate_date("15-01-2026")

    def test_date_range(self):
        with self.assertRaises(ValidationError):
            validate_date_range(TODAY, TODAY - timedelta(days=1))


class LogicTests(unittest.TestCase):
    def test_status_computation(self):
        self.assertEqual(make_notice(2, "b", offset=-3).status, EXPIRED)
        self.assertEqual(make_notice(3, "c", offset=10).status, UPCOMING)
        self.assertEqual(make_notice(4, "d", offset=0).status, ACTIVE)

    def test_search(self):
        items = [make_notice(1, "Midterm Exam"),
                 make_notice(2, "Library", "maintenance")]
        self.assertEqual(len(NoticeService.search(items, keyword="midterm")), 1)
        self.assertEqual(len(NoticeService.search(items, category="maintenance")), 1)

    def test_summary_and_warnings(self):
        items = [make_notice(1, "a", offset=-2), make_notice(2, "b", offset=2)]
        s = NoticeService.summary(items, TODAY)
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["expired"], 1)
        self.assertEqual(s["overdue"], 1)
        self.assertGreaterEqual(len(NoticeService.warnings(items, TODAY)), 2)

    def test_next_id_delete(self):
        items = [make_notice(1, "a"), make_notice(5, "b")]
        self.assertEqual(NoticeService.next_id(items), 6)
        self.assertTrue(NoticeService.delete(items, 1))
        self.assertFalse(NoticeService.delete(items, 99))


class StorageTests(unittest.TestCase):
    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "store.json")
            items = [make_notice(1, "a"), make_notice(2, "b")]
            self.assertTrue(get_backend("json", path).save(items))
            loaded = get_backend("json", path).load()
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].title, "a")
            self.assertEqual(loaded[0].date_posted, items[0].date_posted)

    def test_corrupt_file_is_tolerated(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as fh:
                fh.write("{not valid json")
            self.assertEqual(get_backend("json", path).load(), [])


class ReportingTests(unittest.TestCase):
    def test_exports(self):
        items = [make_notice(1, "a"), make_notice(2, "b", offset=-1)]
        with tempfile.TemporaryDirectory() as d:
            for ext, fn in [("md", export_markdown), ("txt", export_text),
                            ("csv", export_csv)]:
                path = os.path.join(d, f"r.{ext}")
                self.assertTrue(fn(path, items))
                self.assertGreater(os.path.getsize(path), 0)
        self.assertIn("a", format_table(items))


if __name__ == "__main__":
    unittest.main(verbosity=2)
