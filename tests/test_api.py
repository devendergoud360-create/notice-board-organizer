"""End-to-end HTTP API tests (stdlib urllib) including security behaviour."""

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta

from web.server import build_server
from web.security import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        path = os.path.join(cls.tmp.name, "api.json")
        cls.httpd = build_server(0, backend="json", path=path)
        cls.port = cls.httpd.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def _req(self, path, method="GET", body=None, headers=None, opener=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        op = opener or urllib.request.build_opener()
        try:
            with op.open(req, timeout=5) as r:
                return r.status, r.headers, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode()

    def _csrf(self, opener):
        status, headers, _ = self._req("/api/csrf", opener=opener)
        self.assertEqual(status, 200)
        set_cookie = headers.get_all("Set-Cookie") or []
        jar = {}
        for c in set_cookie:
            part = c.split(";")[0]
            k, v = part.split("=", 1)
            jar[k] = v
        return jar

    def test_health_and_static(self):
        status, _, body = self._req("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        status, headers, html = self._req("/")
        self.assertEqual(status, 200)
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_static_traversal_blocked(self):
        status, _, _ = self._req("/static/..%2f..%2fserver.py")
        self.assertEqual(status, 404)

    def test_bearer_required_when_configured(self):
        os.environ["API_BEARER_TOKEN"] = "secret123"
        try:
            status, _, _ = self._req("/api/notices")
            self.assertEqual(status, 401)
            status, _, body = self._req(
                "/api/notices", headers={"Authorization": "Bearer secret123"})
            self.assertEqual(status, 200)
        finally:
            del os.environ["API_BEARER_TOKEN"]

    def test_full_crud_with_csrf(self):
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        cookies = self._csrf(opener)
        csrf = cookies[CSRF_COOKIE]
        hdrs = {
            "X-CSRF-Token": csrf,
            "Cookie": f"{SESSION_COOKIE}={cookies[SESSION_COOKIE]}; {CSRF_COOKIE}={csrf}",
            "Origin": self.base,
        }
        today = date.today()
        payload = {
            "title": "API Test Notice", "category": "events",
            "date_posted": today.isoformat(),
            "expiry_date": (today + timedelta(days=5)).isoformat(),
            "author": "Tester", "description": "created by test",
        }
        status, _, body = self._req("/api/notices", "POST", payload, hdrs, opener)
        self.assertEqual(status, 201, body)
        nid = json.loads(body)["id"]

        status, _, body = self._req(f"/api/notices/{nid}", headers=hdrs, opener=opener)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["title"], "API Test Notice")

        status, _, body = self._req(f"/api/notices/{nid}?risk=1", headers=hdrs, opener=opener)
        self.assertEqual(status, 200)
        self.assertIn("risk_score", json.loads(body))

        status, _, body = self._req(
            f"/api/notices/{nid}", "PUT", {"title": "Updated"}, hdrs, opener)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["title"], "Updated")

        status, _, body = self._req("/api/summary", headers=hdrs, opener=opener)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(json.loads(body)["total"], 1)

        status, _, body = self._req(f"/api/notices/{nid}", "DELETE", headers=hdrs, opener=opener)
        self.assertEqual(status, 200)

    def test_csrf_missing_rejected(self):
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self._csrf(opener)
        payload = {"title": "x", "category": "events",
                   "date_posted": date.today().isoformat(),
                   "expiry_date": (date.today() + timedelta(days=1)).isoformat()}
        status, _, _ = self._req("/api/notices", "POST", payload,
                                 {"Origin": self.base}, opener)
        self.assertEqual(status, 403)

    def test_bad_origin_rejected(self):
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        cookies = self._csrf(opener)
        csrf = cookies[CSRF_COOKIE]
        headers = {
            "X-CSRF-Token": csrf,
            "Cookie": f"{SESSION_COOKIE}={cookies[SESSION_COOKIE]}; {CSRF_COOKIE}={csrf}",
            "Origin": "http://evil.example",
        }
        payload = {"title": "x", "category": "events",
                   "date_posted": date.today().isoformat(),
                   "expiry_date": (date.today() + timedelta(days=1)).isoformat()}
        status, _, _ = self._req("/api/notices", "POST", payload, headers, opener)
        self.assertEqual(status, 403)

    def test_validation_and_body_limit(self):
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        cookies = self._csrf(opener)
        csrf = cookies[CSRF_COOKIE]
        hdrs = {
            "X-CSRF-Token": csrf,
            "Cookie": f"{SESSION_COOKIE}={cookies[SESSION_COOKIE]}; {CSRF_COOKIE}={csrf}",
            "Origin": self.base,
        }
        status, _, _ = self._req(
            "/api/notices", "POST", {"title": "x", "category": "bogus"}, hdrs, opener)
        self.assertEqual(status, 422)
        big = {"title": "x" * 70000, "category": "events"}
        status, _, _ = self._req("/api/notices", "POST", big, hdrs, opener)
        self.assertEqual(status, 413)


if __name__ == "__main__":
    unittest.main(verbosity=2)
