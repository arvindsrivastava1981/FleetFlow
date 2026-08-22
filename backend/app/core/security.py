from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.db.connection import get_db
from backend.app.db.queries import auth_store

AUTH_COOKIE: str = settings.auth_cookie

# token -> {"user_id": int, "username": str, "role": str, "issued_at": float}.
# TTL enforced on read to avoid unbounded growth.
_auth_sessions: dict[str, dict] = {}
_session_lock = threading.Lock()

# Per-IP login attempt tracker for brute-force defense: ip -> (count, locked_until)
_login_attempts: dict[str, tuple[int, float]] = {}
_login_lock = threading.Lock()

# Durable mirror (audit R-1): session/throttle state is also written to
# Postgres (db.queries.auth_store) so restarts and extra instances keep
# working. In-memory dicts remain the hot path; DB access is best-effort.
_logger = logging.getLogger(__name__)
_db_purge_last: float = 0.0
# Simple circuit breaker: after 2 consecutive durable-store failures, skip DB
# attempts for a cooldown so an unreachable DB can't stall request handling.
_db_fail_streak: int = 0
_db_open_until: float = 0.0


def _token_hash(token: str) -> str:
    """Only SHA-256 hashes of tokens are ever persisted, never raw tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def _db(fn, /, *args):
    """Best-effort durable-store call — persistence must never break auth."""
    global _db_fail_streak, _db_open_until
    now = _now()
    if now < _db_open_until:
        return None  # breaker open: fail fast without touching the network
    try:
        with get_db() as conn:
            result = fn(conn, *args)
        _db_fail_streak = 0
        return result
    except Exception as exc:  # noqa: BLE001 - opportunistic by design
        _db_fail_streak += 1
        if _db_fail_streak >= 2:
            _db_open_until = now + 60
            _logger.warning(
                "auth_store unavailable (%s); skipping persistence for 60s", exc
            )
        else:
            _logger.warning(
                "auth_store.%s failed: %s", getattr(fn, "__name__", "?"), exc
            )
        return None


def _maybe_purge_expired() -> None:
    """Opportunistic DB-side cleanup of expired rows (max once per 10 min)."""
    global _db_purge_last
    if _now() - _db_purge_last < 600:
        return
    _db_purge_last = _now()
    _db(auth_store.delete_expired_auth_sessions)


# ---------------------------------------------------------------------------#
# Session management
# ---------------------------------------------------------------------------#
def _now() -> float:
    return time.time()


def create_session(user_id: int, username: str, role: str) -> str:
    """Issue a fresh session token with TTL, binding user identity and role."""
    token = secrets.token_urlsafe(32)
    expires = _now() + settings.session_ttl_hours * 3600
    with _session_lock:
        _auth_sessions[token] = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "issued_at": _now(),
            "expires_at": expires,
        }
    # Durable mirror (audit R-1): the session survives restarts and is visible
    # to other instances via cold-token rehydration in `_get_session_data`.
    expires = _now() + settings.session_ttl_hours * 3600
    _db(
        auth_store.insert_auth_session,
        _token_hash(token),
        user_id,
        username,
        role,
        datetime.now(timezone.utc),
        datetime.fromtimestamp(expires, tz=timezone.utc),
    )
    _maybe_purge_expired()
    return token


def _sweep_expired() -> None:
    """Drop tokens older than the session TTL."""
    cutoff = _now() - settings.session_ttl_hours * 3600
    stale = [t for t, data in _auth_sessions.items() if data["issued_at"] < cutoff]
    for t in stale:
        with _session_lock:
            _auth_sessions.pop(t, None)


def destroy_session(request: Request) -> None:
    """Revoke whichever transport carried the request — cookie OR Bearer."""
    token = request.cookies.get(AUTH_COOKIE) or _bearer_token_from_request(request)
    if token:
        with _session_lock:
            _auth_sessions.pop(token, None)
        _db(auth_store.delete_auth_session, _token_hash(token))


def revoke_user_sessions(user_id: int) -> int:
    """Drop every session token bound to *user_id* (audits B-1 + R-1).

    Called on password change and account deactivation so stale tokens cannot
    outlive the credential / active-state change. Purges both this process's
    dict AND the durable Postgres mirror, making revocation fleet-wide.
    Returns the number of in-process tokens revoked.
    """
    with _session_lock:
        victims = [
            token
            for token, data in _auth_sessions.items()
            if data.get("user_id") == user_id
        ]
        for token in victims:
            _auth_sessions.pop(token, None)
    _db(auth_store.delete_auth_sessions_for_user, user_id)
    return len(victims)


def refresh_session(token: str | None) -> int | None:
    """Sliding renewal (audit E-10): extend a live session's TTL.

    Returns the new epoch expiry, or ``None`` when the token is not currently
    valid. Extends both the memory entry and the durable mirror so other
    instances observe the same new expiry.
    """
    if not token:
        return None
    data = _get_session_data(token)
    if not data:
        return None
    new_expiry = _now() + settings.session_ttl_hours * 3600
    with _session_lock:
        entry = _auth_sessions.get(token)
        if entry is not None:
            entry["expires_at"] = new_expiry
    _db(
        auth_store.insert_auth_session,
        _token_hash(token),
        data["user_id"],
        data["username"],
        data["role"],
        datetime.now(timezone.utc),
        datetime.fromtimestamp(new_expiry, tz=timezone.utc),
    )
    return int(new_expiry)


def _get_session_data(token: str | None) -> dict | None:
    """Return the session dict for *token* if valid, else None."""
    if not token:
        return None
    _sweep_expired()
    with _session_lock:
        data = _auth_sessions.get(token)
    if data is not None:
        # Honor the per-session hard expiry even on the memory hot path.
        if data.get("expires_at", float("inf")) > _now():
            return data
        with _session_lock:
            _auth_sessions.pop(token, None)
        return None
    # Cold token — this process restarted or the request landed on another
    # instance: rehydrate the session from the durable Postgres mirror (R-1).
    row = _db(auth_store.fetch_auth_session, _token_hash(token))
    if not row:
        return None
    data = {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "issued_at": row["issued_at"].timestamp() if row["issued_at"] else _now(),
        "expires_at": (
            row["expires_at"].timestamp() if row["expires_at"] else _now()
        ),
    }
    with _session_lock:
        _auth_sessions[token] = data
    return data


# ---------------------------------------------------------------------------#
# Login brute-force defense
# ---------------------------------------------------------------------------#
def login_allowed(ip: str) -> tuple[bool, int]:
    """Return (allowed, seconds_remaining_lock)."""
    with _login_lock:
        if ip not in _login_attempts:
            # First sight of this IP since (re)start: rehydrate any persisted
            # brute-force counter so a deploy cannot reset an attacker's clock.
            persisted = _db(auth_store.get_login_throttle, ip)
            if persisted is not None:
                _login_attempts[ip] = persisted
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
        remaining = max(0, settings.login_max_attempts - count)
    # Mirror so brute-force progress survives a deploy / spans instances.
    locked_dt = (
        datetime.fromtimestamp(locked_until, tz=timezone.utc)
        if locked_until > 0
        else None
    )
    _db(auth_store.upsert_login_throttle, ip, count, locked_dt)
    return remaining


def clear_login_failures(ip: str) -> None:
    with _login_lock:
        _login_attempts.pop(ip, None)
    _db(auth_store.clear_login_throttle, ip)


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
    (web client, mobile). This keeps the single session store — memory
    hot-path + durable Postgres mirror — shared by both transport paths.
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
