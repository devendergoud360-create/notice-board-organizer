"""Register all built-in storage strategies at import time."""

from .registry import register_backend
from .json_backend import JsonBackend
from .csv_backend import CsvBackend
from .sqlite_backend import SqliteBackend

register_backend("json", JsonBackend)
register_backend("csv", CsvBackend)
register_backend("sqlite", SqliteBackend)
