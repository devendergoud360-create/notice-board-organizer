"""Vercel serverless entrypoint for the Notice Board Organizer API.

Deployment note (docs/SRS.md §17): Vercel is a deliberate deployment target
with its own data layer - an isolated per-instance JSON store under /tmp
seeded from the shipped sample data. It reuses the same application/domain
layers as the loopback server; only the store path and transport guards differ.

Vercel's /api directory requires `handler` to be a BaseHTTPRequestHandler
subclass. We subclass our full APIHandler, inheriting all routing, validation,
CSP headers, HTML escaping, and structured logging behaviour. Because the edge
has no loopback boundary, we additionally enforce an allow-listed Origin check
and an optional bearer token (API_BEARER_TOKEN) on every request.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from application import App  # noqa: E402
from application.events import bus  # noqa: E402
from web.security import check_bearer, constant_time_eq  # noqa: E402
from web.server import APIHandler  # noqa: E402

STORE = "/tmp/nbo_vercel_notices.json"
# Origins permitted to call the edge API (the deployed frontend + localhost dev).
ALLOWED_ORIGINS = {
    "https://notice-board-organizer.vercel.app",
    "https://notice-board-organizer-grwdp4i1s-cherry-ff88.vercel.app",
    "http://127.0.0.1:8765",
    "http://localhost:8765",
}


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

    def _edge_authorized(self) -> bool:
        """Edge transport guards: origin allow-list + optional bearer token."""
        origin = (self.headers.get("Origin") or "").rstrip("/")
        referer = (self.headers.get("Referer") or "").rstrip("/")
        source = origin or referer
        # Requests with no Origin/Referer (curl, health probes) are allowed but
        # logged; browser requests must originate from an allow-listed origin.
        if source:
            host = urlparse(source).netloc
            allowed = any(urlparse(o).netloc == host for o in ALLOWED_ORIGINS)
            if not allowed:
                bus.emit("edge.origin_rejected", {"origin": source})
                self._error(403, "origin not allowed")
                return False
        if not check_bearer(self.headers):
            bus.emit("edge.auth_rejected", {})
            self._error(401, "invalid or missing bearer token")
            return False
        return True

    def _route(self, method):
        if not self._edge_authorized():
            return
        self.app = _build_app()
        return super()._route(method)

    def log_message(self, fmt, *args):
        pass
