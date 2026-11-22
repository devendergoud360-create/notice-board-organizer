"""Vercel serverless entrypoint for the Notice Board Organizer API.

Deployment note (docs/SRS.md): Vercel is a deliberate deployment target with
its own data layer - an isolated per-instance JSON store under /tmp seeded
from the shipped sample data. It reuses the same application/domain layers as
the loopback server; only the store path differs.

Vercel's /api directory requires `handler` to be a BaseHTTPRequestHandler
subclass. We subclass our full APIHandler, inheriting all routing, security
headers, validation, and structured logging behaviour.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from application import App  # noqa: E402
from web.server import APIHandler  # noqa: E402

STORE = "/tmp/nbo_vercel_notices.json"


def _build_app() -> App:
    app = App(backend="json", path=STORE)
    if not app.notices:
        sample = ROOT / "data" / "sample_notices.json"
        if sample.exists():
            with open(sample, "r", encoding="utf-8") as fh:
                app.import_rows(json.load(fh), replace=True)
    return app


class handler(APIHandler):
    """Vercel-compatible handler reusing the full local API behaviour."""

    def _route(self, method):
        self.app = _build_app()
        return super()._route(method)

    def log_message(self, fmt, *args):
        pass
