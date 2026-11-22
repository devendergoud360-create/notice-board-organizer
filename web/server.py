"""Loopback-only HTTP API + static UI presentation layer.

Run: python -m web.server [--port 8765] [--backend json|csv|sqlite]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from application import App, bus
from application.events import FileSink
from domain.entities import parse_date
from web.security import (
    CSRF_COOKIE, CSRF_HEADER, MAX_BODY_BYTES, SESSION_COOKIE,
    check_bearer, check_csrf, check_origin, new_csrf_token,
    safe_static_path, security_headers,
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

ERRORS = {
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 413: "Payload Too Large", 422: "Unprocessable Entity",
    405: "Method Not Allowed", 500: "Internal Server Error",
}


class APIHandler(BaseHTTPRequestHandler):
    server_version = "NBO/1.0"
    app: App

    # ---------- response helpers ----------
    def _send(self, status: int, payload, content_type="application/json; charset=utf-8",
              extra_headers: dict | None = None):
        body = (json.dumps(payload, ensure_ascii=False, default=str)
                if not isinstance(payload, str) else payload)
        data = body.encode("utf-8")
        headers = security_headers(extra_headers)
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(len(data))
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _error(self, status: int, message: str):
        bus.emit("http.error", {"status": status, "message": message,
                                "path": self.path})
        self._send(status, {"error": ERRORS.get(status, "Error"),
                            "message": message, "status": status})

    def _set_csrf_cookies(self):
        session = new_csrf_token()
        csrf = new_csrf_token()
        self.send_header("Set-Cookie",
                         f"{SESSION_COOKIE}={session}; HttpOnly; SameSite=Strict; Path=/")
        self.send_header("Set-Cookie",
                         f"{CSRF_COOKIE}={csrf}; SameSite=Strict; Path=/")
        return csrf

    # ---------- request helpers ----------
    def _authorized(self, state_changing: bool) -> bool:
        if not check_bearer(self.headers):
            self._error(401, "invalid or missing bearer token")
            return False
        if state_changing:
            if not check_origin(self.headers, self.headers.get("Host", "")):
                self._error(403, "origin check failed")
                return False
            if not check_csrf(self.headers):
                self._error(403, "CSRF validation failed")
                return False
        return True

    def _read_body(self):
        length = self.headers.get("Content-Length")
        if length is None:
            return {}
        try:
            size = int(length)
        except ValueError:
            raise ValueError("invalid Content-Length")
        if size > MAX_BODY_BYTES:
            # Drain the oversized body before responding. On Windows, closing a
            # connection with unread inbound data triggers WinError 10053 at the
            # client, which would mask the intended 413 response.
            try:
                self.rfile.read(size)
            except OSError:
                pass
            self._error(413, "request body too large")
            return None
        raw = self.rfile.read(size)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("invalid JSON body")
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    # ---------- dispatch ----------
    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")

    def do_HEAD(self):
        self._route("GET")

    def log_message(self, fmt, *args):
        bus.emit("http.request", {"method": self.command, "path": self.path,
                                  "client": self.client_address[0]})

    def _route(self, method: str):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        state = method in ("POST", "PUT", "DELETE")

        if path == "/api/csrf":
            if method != "GET":
                return self._error(405, "method not allowed")
            csrf = new_csrf_token()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie",
                             f"{SESSION_COOKIE}={new_csrf_token()}; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Set-Cookie",
                             f"{CSRF_COOKIE}={csrf}; SameSite=Strict; Path=/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/" or path == "/index.html":
            return self._serve_static("index.html")
        if path.startswith("/static/"):
            name = path[len("/static/"):]
            safe = safe_static_path(name)
            if not safe:
                return self._error(404, "not found")
            return self._serve_static(safe)

        # All API routes below require bearer + (for state changes) CSRF/origin.
        if not path.startswith("/api/"):
            return self._error(404, "not found")
        if not self._authorized(state):
            return
        # Granular role check: viewers may read only; mutations need admin.
        from application.auth import authorize
        permission = "read" if method == "GET" else (
            "delete" if method == "DELETE" else
            "update" if method == "PUT" else "add")
        if "/api/import" in path:
            permission = "import"
        if "/api/export" in path:
            permission = "export"
        allowed, reason = authorize(self.headers, permission)
        if not allowed:
            bus.emit("auth.denied", {"permission": permission, "reason": reason})
            return self._error(403, reason)

        try:
            return self._api(method, path, qs)
        except ValueError as exc:
            return self._error(422, str(exc))
        except Exception as exc:  # pragma: no cover
            bus.emit("http.unhandled", {"error": str(exc)})
            return self._error(500, "internal server error")

    def _serve_static(self, name: str):
        fp = os.path.join(STATIC_DIR, name)
        if not os.path.isfile(fp):
            return self._error(404, "not found")
        with open(fp, "r", encoding="utf-8") as fh:
            content = fh.read()
        ctype = "text/html; charset=utf-8" if name.endswith(".html") else \
                "application/javascript; charset=utf-8" if name.endswith(".js") else \
                "text/css; charset=utf-8"
        self._send(200, content, ctype)

    def _api(self, method, path, qs):
        app = self.app
        if path == "/api/health" and method == "GET":
            return self._send(200, {"status": "ok", "version": "1.0.0",
                                    "backend": app.backend_name,
                                    "count": len(app.notices)})
        if path == "/api/notices":
            if method == "GET":
                return self._send(200, {"notices": [
                    n.to_dict() for n in app.search(qs.get("keyword", ""), qs.get("category", ""))
                ]})
            if method == "POST":
                body = self._read_body()
                if body is None:
                    return
                try:
                    posted = parse_date(body["date_posted"])
                    expiry = parse_date(body["expiry_date"])
                    from domain.entities import VALID_CATEGORIES
                    if body.get("category") not in VALID_CATEGORIES:
                        return self._error(422, "invalid category")
                    created = app.add(
                        title=str(body["title"]).strip(),
                        category=body["category"], date_posted=posted,
                        expiry_date=expiry, author=str(body.get("author", "Admin")),
                        description=str(body.get("description", "")),
                    )
                except (KeyError, ValueError) as exc:
                    return self._error(422, str(exc))
                return self._send(201, created.to_dict())
            return self._error(405, "method not allowed")

        if path.startswith("/api/notices/"):
            try:
                nid = int(path.split("/")[-1])
            except ValueError:
                return self._error(400, "invalid id")
            notice = app.get(nid)
            if notice is None:
                return self._error(404, "notice not found")
            if method == "GET":
                if qs.get("risk"):
                    return self._send(200, app.risk(nid))
                return self._send(200, notice.to_dict())
            if method == "PUT":
                body = self._read_body()
                if body is None:
                    return
                changes = {k: v for k, v in body.items() if k != "id"}
                if "date_posted" in changes:
                    changes["date_posted"] = parse_date(changes["date_posted"]).isoformat()
                if "expiry_date" in changes:
                    changes["expiry_date"] = parse_date(changes["expiry_date"]).isoformat()
                updated = app.update(nid, **changes)
                return self._send(200, updated.to_dict())
            if method == "DELETE":
                app.delete(nid)
                return self._send(200, {"deleted": nid})
            return self._error(405, "method not allowed")

        if path == "/api/summary" and method == "GET":
            return self._send(200, app.summary())
        if path == "/api/warnings" and method == "GET":
            return self._send(200, {"warnings": app.warnings()})
        if path == "/api/rank" and method == "GET":
            return self._send(200, {"ranked": app.ranked()})
        if path == "/api/risk" and method == "GET":
            try:
                return self._send(200, app.risk(int(qs["id"])))
            except (KeyError, ValueError):
                return self._error(400, "id required")
        if path == "/api/events" and method == "GET":
            return self._send(200, {"events": "structured JSON on stderr / file sink"})
        return self._error(404, "not found")


def build_server(port: int = 8765, backend: str = "json",
                 path: str | None = None, log_path: str | None = None):
    if log_path:
        bus.subscribe("*", FileSink(log_path))
    app = App(backend=backend, path=path, log_path=log_path)
    APIHandler.app = app
    httpd = ThreadingHTTPServer(("127.0.0.1", port), APIHandler)
    # Request handler threads are daemons so shutdown() never hangs on a
    # lingering connection (important under high-concurrency / test loads).
    httpd.daemon_threads = True
    return httpd


def main():
    parser = argparse.ArgumentParser(description="Notice Board Organizer HTTP API")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--backend", default="json", choices=["json", "csv", "sqlite"])
    parser.add_argument("--path", default=None)
    parser.add_argument("--log", default=None)
    args = parser.parse_args()
    httpd = build_server(args.port, args.backend, args.path, args.log)
    bus.emit("server.started", {"port": args.port, "backend": args.backend})
    print(f"Serving on http://127.0.0.1:{args.port} (loopback only)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
