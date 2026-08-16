"""Security primitives — auth, HTML escaping, CSRF, login brute-force defense.

Consolidates and hardens what was inline in `utils.py`:

- `is_admin(request)` / session tokens (with TTL, not a bare unbounded set)
- `require_admin(request)` -> 303 redirect helper for routers
- `csrf_token` generate/validate for every state-changing POST (fixes §2.4)
- `esc(value)` -> html.escape for every DB-sourced value (fixes §2.3 XSS)
- login rate limiting + lockout (fixes §2.2 brute-force gap)

Session store remains process-local for the single-worker, in-memory reactor
app; multi-worker deployments should swap `_admin_sessions` for a shared
store (e.g. DB-backed) without changing call sites.
"""
from __future__ import annotations

import secrets
import threading
import time

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse

from backend.app.core.config import settings

ADMIN_COOKIE: str = settings.admin_cookie

# token -> issued-at (unix seconds). TTL enforced on read to avoid unbounded growth.
_admin_sessions: dict[str, float] = {}
_session_lock = threading.Lock()

# Per-IP login attempt tracker for brute-force defense: ip -> (count, locked_until)
_login_attempts: dict[str, tuple[int, float]] = {}
_login_lock = threading.Lock()

# Per-request CSRF token store for POST endpoints.
_csrf_tokens: set[str] = set()
_csrf_lock = threading.Lock()


# ---------------------------------------------------------------------------#
# Session management
# ---------------------------------------------------------------------------#
def _now() -> float:
    return time.time()


def create_session() -> str:
    """Issue a fresh admin session token with TTL."""
    token = secrets.token_urlsafe(32)
    with _session_lock:
        _admin_sessions[token] = _now()
    return token


def _sweep_expired() -> None:
    """Drop tokens older than the session TTL."""
    cutoff = _now() - settings.session_ttl_hours * 3600
    stale = [t for t, ts in _admin_sessions.items() if ts < cutoff]
    for t in stale:
        _admin_sessions.pop(t, None)


def destroy_session(request: Request) -> None:
    token = request.cookies.get(ADMIN_COOKIE)
    if token:
        _admin_sessions.pop(token, None)


def is_valid_token(token: str | None) -> bool:
    if not token:
        return False
    _sweep_expired()
    return token in _admin_sessions


def is_admin(request: Request) -> bool:
    return is_valid_token(request.cookies.get(ADMIN_COOKIE))


def require_admin(request: Request, login_url: str = "/login") -> RedirectResponse | None:
    """Return a 303 redirect if unauthenticated, else None.

    Router usage:
        guard = require_admin(request)
        if guard:
            return guard
    """
    if not is_admin(request):
        return RedirectResponse(url=login_url, status_code=303)
    return None


# ---------------------------------------------------------------------------#
# Login brute-force defense
# ---------------------------------------------------------------------------#
def login_allowed(ip: str) -> tuple[bool, int]:
    """Return (allowed, seconds_remaining_lock)."""
    with _login_lock:
        count, locked_until = _login_attempts.get(ip, (0, 0.0))
    if locked_until > _now():
        return False, int(locked_until - _now())
    return True, 0


def register_login_failure(ip: str) -> int:
    """Record a failed attempt; return attempts remaining before lock."""
    with _login_lock:
        count, locked_until = _login_attempts.get(ip, (0, 0.0))
        count += 1
        if count >= settings.login_max_attempts:
            locked_until = _now() + settings.login_lockout_seconds
            count = 0
        _login_attempts[ip] = (count, locked_until)
        return max(0, settings.login_max_attempts - count)


def clear_login_failures(ip: str) -> None:
    with _login_lock:
        _login_attempts.pop(ip, None)


# ---------------------------------------------------------------------------#
# CSRF (mitigation for unauthenticated/data-wiping GET/POST routes, §2.4)
# ---------------------------------------------------------------------------#
def issue_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    with _csrf_lock:
        _csrf_tokens.add(token)
    return token


def validate_csrf_token(token: str | None) -> bool:
    if not token:
        return False
    with _csrf_lock:
        if token in _csrf_tokens:
            _csrf_tokens.discard(token)  # single-use
            return True
    return False


# ---------------------------------------------------------------------------#
# Output encoding (fixes stored-XSS, §2.3)
# ---------------------------------------------------------------------------#
def esc(value) -> str:
    """html.escape a dynamic/DB value for safe interpolation into HTML."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# Dependency alias so routers read cleanly as `request: Request = Depends(admin_auth)`.
def admin_auth(request: Request) -> Request:
    guard = require_admin(request)
    if guard is not None:
        raise UnauthorizedRedirect(guard)
    return request


class UnauthorizedRedirect(Exception):
    """Marker exception carrying the redirect response for dependency handling."""

    def __init__(self, response: RedirectResponse) -> None:
        self.response = response
        super().__init__()