"""Granular authorization roles (Viewer vs Admin).

The optional bearer token may carry a role via the ``X-Role`` header or a
``role`` claim embedded in the token as ``token:role``. When no token is
configured, the app runs in single-user Admin mode for backwards compatibility.

Roles:
  viewer - read-only access (GET endpoints)
  admin  - full access including mutations, import, and export
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Iterable

from web.security import check_bearer, constant_time_eq


class Role(str, Enum):
    VIEWER = "viewer"
    ADMIN = "admin"


PERMISSIONS: dict[str, tuple[Role, ...]] = {
    "read": (Role.VIEWER, Role.ADMIN),
    "add": (Role.ADMIN,),
    "update": (Role.ADMIN,),
    "delete": (Role.ADMIN,),
    "import": (Role.ADMIN,),
    "export": (Role.ADMIN,),
}


def role_from_headers(headers) -> Role:
    """Resolve the caller's role from the bearer token / role header."""
    raw = headers.get("X-Role", "").strip().lower()
    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer ") and ":" in auth:
        raw = auth.split("Bearer ", 1)[1].split(":", 1)[1].strip().lower()
    try:
        return Role(raw)
    except ValueError:
        return Role.ADMIN  # default when no explicit role is supplied


def has_permission(role: Role, permission: str) -> bool:
    allowed: Iterable[Role] = PERMISSIONS.get(permission, (Role.ADMIN,))
    return role in allowed


def authorize(headers, permission: str) -> tuple[bool, str]:
    """Return (allowed, reason). Enforces token validity + role permission."""
    if not check_bearer(headers):
        return False, "invalid or missing bearer token"
    role = role_from_headers(headers)
    if not has_permission(role, permission):
        return False, f"role '{role.value}' lacks permission '{permission}'"
    return True, ""
