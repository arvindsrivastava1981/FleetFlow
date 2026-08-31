from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from datetime import datetime, timezone

from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.db.connection import get_db
from backend.app.db.queries import auth_store

AUTH_COOKIE = settings.auth_cookie
_auth_sessions: dict = {}
_session_lock = threading.Lock()
_login_attempts: dict = {}
_login_lock = threading.Lock()
_logger = logging.getLogger(__name__)
_db_purge_last: float = 0.0
_db_fail_streak = 0
_db_open_until: float = 0.0
BEARER_PREFIX = "Bearer "


def _token_hash(token): return hashlib.sha256(token.encode()).hexdigest()

def _now(): return time.time()


def _db(fn, *args):
    global _db_fail_streak, _db_open_until
    now = _now()
    if now < _db_open_until:
        return None
    try:
        with get_db() as conn:
            result = fn(conn, *args)
        _db_fail_streak = 0
        return result
    except Exception as exc:
        _db_fail_streak += 1
        if _db_fail_streak >= 2:
            _db_open_until = now + 60
            _logger.warning("auth_store unavailable (%s)", exc)
        return None


def _maybe_purge_expired():
    global _db_purge_last
    if _now() - _db_purge_last < 600:
        return
    _db_purge_last = _now()
    _db(auth_store.delete_expired_auth_sessions)


def create_session(user_id, email, role):
    token = secrets.token_urlsafe(32)
    expires = _now() + settings.session_ttl_hours * 3600
    now_ts = _now()
    with _session_lock:
        _auth_sessions[token] = {"user_id": user_id, "email": email, "role": role, "issued_at": now_ts, "expires_at": expires}
    _db(auth_store.insert_auth_session, _token_hash(token), user_id, role,
        datetime.fromtimestamp(now_ts, tz=timezone.utc),
        datetime.fromtimestamp(expires, tz=timezone.utc))
    return token


def _get_session_data(token):
    if not token:
        return None
    now = _now()
    with _session_lock:
        data = _auth_sessions.get(token)
    if data is None:
        row = _db(auth_store.fetch_auth_session, _token_hash(token))
        _maybe_purge_expired()
        if row is None:
            return None
        issued = row["issued_at"].timestamp() if hasattr(row["issued_at"], "timestamp") else 0.0
        expires = row["expires_at"].timestamp() if hasattr(row["expires_at"], "timestamp") else 0.0
        if expires <= now:
            return None
        data = {"user_id": row["user_id"], "role": row["role"], "issued_at": issued, "expires_at": expires}
        with _session_lock:
            _auth_sessions[token] = data
        return data
    if data["expires_at"] <= now:
        with _session_lock:
            _auth_sessions.pop(token, None)
        return None
    return data


def destroy_session(request):
    token = request.cookies.get(AUTH_COOKIE) or _bearer_token_from_request(request)
    if not token:
        return
    with _session_lock:
        _auth_sessions.pop(token, None)
    _db(auth_store.delete_auth_session, _token_hash(token))


def revoke_user_sessions(user_id):
    with _session_lock:
        to_drop = [t for t, d in _auth_sessions.items() if d["user_id"] == user_id]
        for t in to_drop:
            _auth_sessions.pop(t, None)
    _db(auth_store.delete_auth_sessions_for_user, user_id)


def login_allowed(ip):
    now = _now()
    with _login_lock:
        state = _login_attempts.get(ip)
        if state is None:
            row = _db(auth_store.get_login_throttle, ip)
            if row is not None:
                state = (row[0], row[1])
                _login_attempts[ip] = state
        if state is not None and state[1] > now:
            return False, state[1] - now
    return True, 0.0


def register_login_failure(ip):
    now = _now()
    max_at = settings.login_max_attempts
    lockout = settings.login_lockout_seconds
    with _login_lock:
        count, locked = _login_attempts.get(ip, (0, 0.0))
        count += 1
        if count >= max_at:
            locked = now + lockout
        _login_attempts[ip] = (count, locked)
        _db(auth_store.upsert_login_throttle, ip, count,
            datetime.fromtimestamp(locked, tz=timezone.utc) if locked > now else None)
        return max(0, max_at - count)


def clear_login_failures(ip):
    with _login_lock:
        _login_attempts.pop(ip, None)
    _db(auth_store.clear_login_throttle, ip)


def _bearer_token_from_request(request):
    authz = request.headers.get("authorization") or ""
    if authz.casefold().startswith(BEARER_PREFIX.casefold()):
        return authz[len(BEARER_PREFIX):].strip()
    return None


def get_current_user(request):
    token = request.cookies.get(AUTH_COOKIE) or _bearer_token_from_request(request)
    return _get_session_data(token)


def is_authorized_user(request):
    return get_current_user(request) is not None


def require_json_auth(request):
    if not is_authorized_user(request):
        return JSONResponse(status_code=401, content={"error": "unauthorized", "code": "UNAUTHORIZED"})
    return None


def require_json_role(request, *roles):
    user = get_current_user(request)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized", "code": "UNAUTHORIZED"})
    if user["role"] not in roles:
        return JSONResponse(status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"})
    return None


def esc(value):
    if value is None:
        return ""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&#x27;")


def verify_razorpay_webhook(body, signature, timestamp):
    secret = settings.razorpay_webhook_secret
    if not secret or not signature or not timestamp:
        return False
    if not isinstance(body, bytes):
        body = body.encode()
    signed_bytes = f"{body.decode('utf-8', errors='ignore')}|{timestamp}".encode()
    expected = hmac.new(secret.encode(), signed_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def refresh_session(token):
    if not token:
        return None
    now = _now()
    with _session_lock:
        data = _auth_sessions.get(token)
    if data is None or data["expires_at"] <= now:
        return None
    new_expires = now + settings.session_ttl_hours * 3600
    data["expires_at"] = new_expires
    _db(auth_store.insert_auth_session, _token_hash(token), data["user_id"], data["role"],
        datetime.fromtimestamp(data["issued_at"], tz=timezone.utc),
        datetime.fromtimestamp(new_expires, tz=timezone.utc))
    return int(new_expires)
