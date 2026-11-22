"""Tests for the async event bus and granular Viewer/Admin authorization."""

import os
import tempfile
import unittest

from application.auth import Role, authorize, has_permission, role_from_headers
from application.events import EventBus, FileSink


class AsyncBusTest(unittest.TestCase):
    def test_async_delivery(self):
        bus = EventBus(async_mode=True)
        received = []
        bus.subscribe("test", lambda e: received.append(e.data["n"]))
        for i in range(50):
            bus.emit("test", {"n": i})
        self.assertTrue(bus.flush(timeout=5))
        self.assertEqual(sorted(received), list(range(50)))
        bus.shutdown()

    def test_sync_delivery(self):
        bus = EventBus(async_mode=False)
        seen = []
        bus.subscribe("x", lambda e: seen.append(e.name))
        bus.emit_sync("x")
        self.assertEqual(seen, ["x"])

    def test_file_sink_from_worker(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.jsonl")
            bus = EventBus(async_mode=True)
            bus.subscribe("*", FileSink(path))
            for i in range(20):
                bus.emit("evt", {"n": i})
            bus.flush(timeout=5)
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            self.assertEqual(len(lines), 20)
            bus.shutdown()


class AuthTest(unittest.TestCase):
    def test_role_permissions(self):
        self.assertTrue(has_permission(Role.VIEWER, "read"))
        self.assertFalse(has_permission(Role.VIEWER, "add"))
        self.assertFalse(has_permission(Role.VIEWER, "delete"))
        self.assertTrue(has_permission(Role.ADMIN, "delete"))
        self.assertTrue(has_permission(Role.ADMIN, "import"))

    def test_role_from_token_and_header(self):
        class H(dict):
            def get(self, k, d=None):
                return super().get(k, d)
        self.assertEqual(role_from_headers({"X-Role": "viewer"}), Role.VIEWER)
        self.assertEqual(
            role_from_headers({"Authorization": "Bearer tok:viewer"}), Role.VIEWER)

    def test_authorize_without_token_configured(self):
        os.environ.pop("API_BEARER_TOKEN", None)
        ok, _ = authorize({"X-Role": "viewer"}, "read")
        self.assertTrue(ok)
        ok, reason = authorize({"X-Role": "viewer"}, "delete")
        self.assertFalse(ok)
        self.assertIn("lacks permission", reason)

    def test_authorize_with_token(self):
        os.environ["API_BEARER_TOKEN"] = "s3cr3t"
        try:
            ok, _ = authorize({"Authorization": "Bearer s3cr3t", "X-Role": "admin"},
                              "delete")
            self.assertTrue(ok)
            ok, _ = authorize({"Authorization": "Bearer wrong", "X-Role": "admin"},
                              "delete")
            self.assertFalse(ok)
        finally:
            del os.environ["API_BEARER_TOKEN"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
