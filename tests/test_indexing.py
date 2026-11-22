"""Tests proving the SQLite backend uses database indexes for scalability."""

import os
import tempfile
import unittest
from datetime import date, timedelta

import persistence.bootstrap  # noqa: F401
from persistence import get_backend
from seed_data import generate


class IndexingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "indexed.db")
        self.backend = get_backend("sqlite", self.path)
        self.records = generate(40, seed=7)
        self.assertTrue(self.backend.save(self.records))

    def tearDown(self):
        self.tmp.cleanup()

    def test_indexes_exist(self):
        import sqlite3
        conn = sqlite3.connect(self.path)
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        conn.close()
        for expected in (
            "idx_notices_category", "idx_notices_expiry",
            "idx_notices_status", "idx_notices_category_expiry",
            "idx_notices_posted",
        ):
            self.assertIn(expected, names)

    def test_query_plans_use_indexes(self):
        plan = " ".join(self.backend.explain_index_usage(
            "SELECT * FROM notices WHERE category = ?", ("events",))).lower()
        self.assertIn("idx_notices_category", plan)

        plan = " ".join(self.backend.explain_index_usage(
            "SELECT * FROM notices WHERE expiry_date < ?",
            (date.today().isoformat(),))).lower()
        self.assertIn("idx_notices_expiry", plan)

        plan = " ".join(self.backend.explain_index_usage(
            "SELECT * FROM notices WHERE status = ?", ("Active",))).lower()
        self.assertIn("idx_notices_status", plan)

    def test_indexed_queries_return_correct_rows(self):
        results = self.backend.query_by_category("events")
        self.assertTrue(results)
        self.assertTrue(all(n.category == "events" for n in results))

        future = date.today() + timedelta(days=365)
        results = self.backend.query_expiring_before(future)
        self.assertTrue(all(n.expiry_date < future for n in results))

        results = self.backend.query_by_status("Expired")
        self.assertTrue(all(n.status == "Expired" for n in results))


if __name__ == "__main__":
    unittest.main(verbosity=2)
