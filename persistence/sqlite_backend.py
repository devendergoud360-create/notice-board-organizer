"""SQLite storage backend (third interchangeable Strategy)."""

from __future__ import annotations

import os
import sqlite3
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
        return conn

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
