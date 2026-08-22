from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from backend.app.core.config import settings

AUTH_COOKIE: str = settings.auth_cookie

# token -> {"user_id": int, "username": str, "role": str, "issued_at": float}.
# TTL enforced on read to avoid unbounded growth.
_auth_sessions: dict[str, dict] = {}
_session_lock = threading.Lock()

# Per-IP login attempt tracker for brute-force defense: ip -> (count, locked_until)
_login_attempts: dict[str, tuple[int, float]] = {}
_login_lock = threading.Lock()


# ---------------------------------------------------------------------------#
# Session management
# ---------------------------------------------------------------------------#
def _now() -> float:
    return time.time()


def create_session(user_id: int, username: str, role: str) -> str:
    """Issue a fresh session token with TTL, binding user identity and role."""
    token = secrets.token_urlsafe(32)
    with _session_lock:
        _auth_sessions[token] = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "issued_at": _now(),
        }
    return token


def _sweep_expired() -> None:
    """Drop tokens older than the session TTL."""
    cutoff = _now() - settings.session_ttl_hours * 3600
    stale = [t for t, data in _auth_sessions.items() if data["issued_at"] < cutoff]
    for t in stale:
        with _session_lock:
            _auth_sessions.pop(t, None)


def destroy_session(request: Request) -> None:
    token = request.cookies.get(AUTH_COOKIE)
    if token:
        with _session_lock:
            _auth_sessions.pop(token, None)


def _get_session_data(token: str | None) -> dict | None:
    """Return the session dict for *token* if valid, else None."""
    if not token:
        return None
    _sweep_expired()
    with _session_lock:
        return _auth_sessions.get(token)


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
# Mixed auth resolution (cookie OR Authorization Bearer) for /api/v1 JSON routes
# ---------------------------------------------------------------------------#
BEARER_PREFIX: str = "Bearer "


def _bearer_token_from_request(request: Request) -> str | None:
    """Extract the session token from an `Authorization: Bearer <token>` header."""
    authz = request.headers.get("authorization") or ""
    if authz.casefold().startswith(BEARER_PREFIX.casefold()):
        return authz[len(BEARER_PREFIX):].strip()
    return None


def get_current_user(request: Request) -> dict | None:
    """Return the bound user dict {user_id, username, role} or None.

    Accepts auth from either the session cookie (browser) or a Bearer header
    (web client, mobile). This keeps the single in-memory session store shared
    by both transport paths.
    """
    token = request.cookies.get(AUTH_COOKIE) or _bearer_token_from_request(request)
    return _get_session_data(token)


def is_authorized_user(request: Request) -> bool:
    return get_current_user(request) is not None


def require_json_auth(request: Request) -> JSONResponse | None:
    """Return a 401 JSON response if unauthenticated, else None.

    For /api/v1/* endpoints consumed by web/mobile clients. We never return the
    browser-style 303 redirect here — a client-side fetch() cannot follow one
    cleanly and would misreport the response.
    """
    if not is_authorized_user(request):
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "code": "UNAUTHORIZED"},
        )
    return None


def require_json_role(request: Request, *roles: str) -> JSONResponse | None:
    """Return 401/403 JSON if unknown or role not in *roles* (for /api/v1)."""
    user = get_current_user(request)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "code": "UNAUTHORIZED"},
        )
    if user["role"] not in roles:
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "code": "FORBIDDEN"},
        )
    return None
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


def verify_razorpay_webhook(body: bytes, signature: str | None, timestamp: str | None) -> bool:
    """Verify a Razorpay webhook signature (HMAC-SHA256 of `body|timestamp`).

    Razorpay signs each webhook with the webhook secret:
        signed_bytes = f"{body}|{timestamp}".encode()
        expected     = hmac_sha256(signed_bytes, webhook_secret).hexdigest()
    Returns False (never raises) when the payload is forged or untrusted.
    """
    secret = settings.razorpay_webhook_secret
    if not secret or not signature or not timestamp:
        return False
    if not isinstance(body, bytes):
        body = body.encode()
    signed_bytes = f"{body.decode('utf-8', errors='ignore')}|{timestamp}".encode()
    expected = hmac.new(secret.encode(), signed_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)