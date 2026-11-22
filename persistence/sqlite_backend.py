"""SQLite storage backend (third interchangeable Strategy).

Includes database indexes on the high-selectivity columns used by search,
filtering, and expiry queries so lookups remain efficient at large scale:
  - idx_notices_category          (category)
  - idx_notices_expiry            (expiry_date)
  - idx_notices_status            (status)
  - idx_notices_category_expiry   (category, expiry_date) composite
  - idx_notices_posted            (date_posted)
The query methods below use these indexes (verified via EXPLAIN QUERY PLAN).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date
from typing import List

from domain import Notice
from .base import StorageBackend


class SqliteBackend(StorageBackend):
    name = "sqlite"

    def __init__(self, path: str):
        self.path = path

    def location(self) -> str:
        return self.path

    def _connect(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                category TEXT NOT NULL, date_posted TEXT NOT NULL,
                expiry_date TEXT NOT NULL, status TEXT NOT NULL,
                author TEXT, description TEXT
            )
        """)
        # Indexes for scalable filtering/sorting (see module docstring).
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_notices_category "
            "ON notices(category)",
            "CREATE INDEX IF NOT EXISTS idx_notices_expiry "
            "ON notices(expiry_date)",
            "CREATE INDEX IF NOT EXISTS idx_notices_status "
            "ON notices(status)",
            "CREATE INDEX IF NOT EXISTS idx_notices_category_expiry "
            "ON notices(category, expiry_date)",
            "CREATE INDEX IF NOT EXISTS idx_notices_posted "
            "ON notices(date_posted)",
        ):
            conn.execute(stmt)
        return conn

    # ------------------------------------------------------------------
    # Indexed query methods (O(log n) index lookups for large datasets).
    # ------------------------------------------------------------------
    def query_by_category(self, category: str) -> List[Notice]:
        """Fetch notices by category using idx_notices_category."""
        conn = None
        try:
            conn = self._connect()
            cur = conn.execute(
                "SELECT id,title,category,date_posted,expiry_date,status,"
                "author,description FROM notices WHERE category = ? ORDER BY id",
                (category.lower(),),
            )
            return [Notice.from_dict(dict(zip(
                ["id", "title", "category", "date_posted", "expiry_date",
                 "status", "author", "description"], row))) for row in cur.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            if conn is not None:
                conn.close()

    def query_expiring_before(self, before: date) -> List[Notice]:
        """Fetch notices expiring before a date using idx_notices_expiry."""
        conn = None
        try:
            conn = self._connect()
            cur = conn.execute(
                "SELECT id,title,category,date_posted,expiry_date,status,"
                "author,description FROM notices WHERE expiry_date < ? "
                "ORDER BY expiry_date",
                (before.isoformat(),),
            )
            return [Notice.from_dict(dict(zip(
                ["id", "title", "category", "date_posted", "expiry_date",
                 "status", "author", "description"], row))) for row in cur.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            if conn is not None:
                conn.close()

    def query_by_status(self, status: str) -> List[Notice]:
        """Fetch notices by status using idx_notices_status."""
        conn = None
        try:
            conn = self._connect()
            cur = conn.execute(
                "SELECT id,title,category,date_posted,expiry_date,status,"
                "author,description FROM notices WHERE status = ? ORDER BY id",
                (status,),
            )
            return [Notice.from_dict(dict(zip(
                ["id", "title", "category", "date_posted", "expiry_date",
                 "status", "author", "description"], row))) for row in cur.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            if conn is not None:
                conn.close()

    def explain_index_usage(self, query: str, params: tuple = ()) -> List[str]:
        """Return EXPLAIN QUERY PLAN rows (used by tests to prove indexing)."""
        conn = None
        try:
            conn = self._connect()
            return [row[3] for row in
                    conn.execute("EXPLAIN QUERY PLAN " + query, params).fetchall()]
        finally:
            if conn is not None:
                conn.close()

    def load(self) -> List[Notice]:
        notices = []
        conn = None
        try:
            conn = self._connect()
            cur = conn.execute(
                "SELECT id,title,category,date_posted,expiry_date,"
                "status,author,description FROM notices ORDER BY id"
            )
            for row in cur.fetchall():
                rec = dict(zip(
                    ["id", "title", "category", "date_posted", "expiry_date",
                     "status", "author", "description"], row
                ))
                try:
                    n = Notice.from_dict(rec)
                    n.validate()
                    notices.append(n)
                except ValueError:
                    continue
        except sqlite3.Error:
            return []
        finally:
            if conn is not None:
                conn.close()
        return notices

    def save(self, notices: List[Notice]) -> bool:
        conn = None
        try:
            conn = self._connect()
            conn.execute("DELETE FROM notices")
            conn.executemany(
                "INSERT INTO notices VALUES (?,?,?,?,?,?,?,?)",
                [tuple(n.to_dict()[k] for k in [
                    "id", "title", "category", "date_posted", "expiry_date",
                    "status", "author", "description"]) for n in notices],
            )
            conn.commit()
            return True
        except sqlite3.Error:
            if conn is not None:
                conn.rollback()
            return False
        finally:
            if conn is not None:
                conn.close()
