"""Security helpers for the local HTTP API.

- Loopback-only binding (server binds 127.0.0.1).
- Origin checks on state-changing requests.
- Double-submit CSRF: HttpOnly session cookie + readable CSRF cookie echoed
  in the X-CSRF-Token header.
- Optional bearer token via API_BEARER_TOKEN env var.
- Static-file whitelist (no path traversal).
- Request body size limit.
- Strict Content-Security-Policy.
- HTML escaping of user text (via html.escape in render layer).
"""

from __future__ import annotations

import hmac
import os
from http import cookies
from urllib.parse import urlparse

MAX_BODY_BYTES = 64 * 1024
SESSION_COOKIE = "nbo_session"
CSRF_COOKIE = "nbo_csrf"
CSRF_HEADER = "X-CSRF-Token"
STATIC_WHITELIST = {"index.html", "app.js", "styles.css"}
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'; object-src 'none'"
)


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def new_csrf_token() -> str:
    return os.urandom(24).hex()


def parse_cookies(header: str | None) -> dict:
    jar = cookies.SimpleCookie()
    try:
        jar.load(header or "")
    except cookies.CookieError:
        return {}
    return {k: v.value for k, v in jar.items()}


def check_origin(headers, host: str) -> bool:
    """Reject state-changing requests from foreign origins."""
    origin = headers.get("Origin")
    if not origin:
        return True  # same-origin browser requests may omit Origin
    parsed = urlparse(origin)
    return parsed.netloc in (host, f"127.0.0.1:{host.split(':')[-1]}") or parsed.netloc == host


def check_csrf(headers) -> bool:
    cookies_map = parse_cookies(headers.get("Cookie"))
    csrf_cookie = cookies_map.get(CSRF_COOKIE)
    csrf_header = headers.get(CSRF_HEADER)
    session = cookies_map.get(SESSION_COOKIE)
    if not (csrf_cookie and csrf_header and session):
        return False
    return constant_time_eq(csrf_cookie, csrf_header)


def check_bearer(headers) -> bool:
    """Optional bearer token. If env var unset, auth is not required."""
    expected = os.environ.get("API_BEARER_TOKEN")
    if not expected:
        return True
    provided = headers.get("Authorization", "")
    if not provided.startswith("Bearer "):
        return False
    return constant_time_eq(provided[7:], expected)


def safe_static_path(name: str) -> str | None:
    """Return a whitelisted static filename or None (blocks traversal)."""
    base = os.path.basename(name)
    if base in STATIC_WHITELIST and base == name:
        return base
    return None


def security_headers(extra: dict | None = None) -> dict:
    headers = {
        "Content-Security-Policy": CSP,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }
    if extra:
        headers.update(extra)
    return headers
