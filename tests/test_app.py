"""Smoke tests for the Notice Board Organizer (stdlib unittest)."""

import os
import tempfile
import unittest
from datetime import date, timedelta

import logic
import reporting
import storage
from models import Notice, ACTIVE, EXPIRED, UPCOMING
from validation import (
    ValidationError, validate_category, validate_date,
    validate_date_range, validate_text,
)

TODAY = date.today()


def make_notice(nid, title, category="academics", offset=5, posted=None):
    expiry = TODAY + timedelta(days=offset)
    return Notice(
        id=nid, title=title, category=category,
        date_posted=posted or (TODAY - timedelta(days=10)),
        expiry_date=expiry, status="Active",
    )


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
        self.assertEqual(make_notice(1, "a", offset=-1).status, "Active")  # set later
        past = make_notice(2, "b", offset=-3)
        past.refresh_status(TODAY)
        self.assertEqual(past.status, EXPIRED)
        future = make_notice(3, "c", offset=10)
        future.refresh_status(TODAY)
        self.assertEqual(future.status, UPCOMING)
        today_n = make_notice(4, "d", offset=0)
        today_n.refresh_status(TODAY)
        self.assertEqual(today_n.status, ACTIVE)

    def test_search(self):
        items = [make_notice(1, "Midterm Exam"), make_notice(2, "Library", "maintenance")]
        self.assertEqual(len(logic.search(items, keyword="midterm")), 1)
        self.assertEqual(len(logic.search(items, category="maintenance")), 1)

    def test_summary_and_warnings(self):
        items = [make_notice(1, "a", offset=-2), make_notice(2, "b", offset=2)]
        s = logic.summary(items)
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["expired"], 1)
        self.assertEqual(s["overdue"], 1)
        self.assertGreaterEqual(len(logic.warnings(items)), 2)

    def test_next_id_delete(self):
        items = [make_notice(1, "a"), make_notice(5, "b")]
        self.assertEqual(logic.next_id(items), 6)
        self.assertTrue(logic.delete_notice(items, 1))
        self.assertFalse(logic.delete_notice(items, 99))


class StorageTests(unittest.TestCase):
    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "store.json")
            items = [make_notice(1, "a"), make_notice(2, "b")]
            self.assertTrue(storage.save_json(path, items))
            loaded = storage.load_json(path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].title, "a")
            self.assertEqual(loaded[0].date_posted, items[0].date_posted)

    def test_corrupt_file_is_tolerated(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as fh:
                fh.write("{not valid json")
            self.assertEqual(storage.load_json(path), [])


class ReportingTests(unittest.TestCase):
    def test_exports(self):
        items = [make_notice(1, "a"), make_notice(2, "b", offset=-1)]
        with tempfile.TemporaryDirectory() as d:
            for ext, fn in [("md", reporting.export_markdown),
                            ("txt", reporting.export_text),
                            ("csv", reporting.export_csv)]:
                path = os.path.join(d, f"r.{ext}")
                self.assertTrue(fn(path, items))
                self.assertGreater(os.path.getsize(path), 0)
        self.assertIn("a", reporting.format_table(items))


if __name__ == "__main__":
    unittest.main(verbosity=2)
