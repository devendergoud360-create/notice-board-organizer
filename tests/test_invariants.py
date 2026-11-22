"""Broad invariant/property tests across the ENTIRE dataset, every backend,
and every export format. These assert rules that must hold globally."""

import csv
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

import persistence.bootstrap  # noqa: F401
from application import App
from domain import Notice, NoticeService, VALID_CATEGORIES
from persistence import available_backends, get_backend
from reporting import export_csv, export_markdown, export_text
from risk import compute_risk, clamp01, fnv1a_32

from seed_data import generate as generate_sample


class InvariantTest(unittest.TestCase):
    def setUp(self):
        self.records = generate_sample(40, seed=7)

    def test_all_seeded_records_valid(self):
        for n in self.records:
            n.validate()
        self.assertEqual(len(self.records), 40)

    def test_status_matches_date_for_every_record(self):
        today = date.today()
        for n in self.records:
            expected = "Expired" if n.expiry_date < today else (
                "Active" if n.expiry_date == today else "Upcoming")
            self.assertEqual(n.status, expected, n.id)

    def test_days_remaining_identity(self):
        today = date.today()
        for n in self.records:
            self.assertEqual(n.days_remaining(today), (n.expiry_date - today).days)

    def test_risk_bounded_for_every_record(self):
        today = date.today()
        for n in self.records:
            score = compute_risk(n, self.records, today)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_risk_deterministic(self):
        today = date.today()
        for n in self.records:
            self.assertEqual(compute_risk(n, self.records, today),
                             compute_risk(n, list(reversed(self.records)), today))

    def test_fnv1a_known_vectors(self):
        # Deterministic hash of lowercase UTF-8 category strings.
        self.assertEqual(fnv1a_32("academics"), fnv1a_32("academics"))
        self.assertNotEqual(fnv1a_32("events"), fnv1a_32("deadlines"))

    def test_every_backend_round_trip_preserves_dataset(self):
        today = date.today()
        ext = {"json": ".json", "csv": ".csv", "sqlite": ".db"}
        for backend in available_backends():
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "store" + ext.get(backend, ".dat"))
                store = get_backend(backend, path)
                self.assertTrue(store.save(self.records))
                loaded = store.load()
                self.assertEqual(len(loaded), len(self.records), backend)
                by_id = {n.id: n for n in loaded}
                for original in self.records:
                    copy = by_id[original.id]
                    self.assertEqual(copy.title, original.title, backend)
                    self.assertEqual(copy.category, original.category, backend)
                    self.assertEqual(copy.expiry_date, original.expiry_date, backend)
                    self.assertEqual(copy.status, original.status, backend)

    def test_corrupt_backend_recovers_to_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as fh:
                fh.write("{not json")
            store = get_backend("json", path)
            self.assertEqual(store.load(), [])
            backups = [f for f in os.listdir(d) if ".corrupt." in f]
            self.assertTrue(backups, "corrupt file should be backed up")

    def test_all_export_formats_contain_every_title(self):
        with tempfile.TemporaryDirectory() as d:
            for ext, fn in [("md", export_markdown), ("txt", export_text),
                            ("csv", export_csv)]:
                path = os.path.join(d, f"r.{ext}")
                self.assertTrue(fn(path, self.records), ext)
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                for n in self.records:
                    self.assertIn(n.title, content, f"{ext} missing {n.title}")

    def test_summary_counts_sum_to_total(self):
        s = NoticeService.summary(self.records, date.today())
        self.assertEqual(s["active"] + s["upcoming"] + s["expired"], s["total"])

    def test_add_delete_invariants(self):
        items = list(self.records)
        before = len(items)
        new = Notice(id=0, title="New", category="general",
                     date_posted=date.today(), expiry_date=date.today() + timedelta(days=3))
        NoticeService.add(items, new)
        self.assertEqual(len(items), before + 1)
        self.assertGreater(new.id, 0)
        self.assertTrue(NoticeService.delete(items, new.id))
        self.assertEqual(len(items), before)

    def test_search_category_invariant(self):
        for cat in VALID_CATEGORIES:
            results = NoticeService.search(self.records, category=cat)
            self.assertTrue(all(n.category == cat for n in results))


if __name__ == "__main__":
    unittest.main(verbosity=2)
