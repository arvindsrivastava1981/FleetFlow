from __future__ import annotations

import hashlib, secrets, time
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from backend.app.api.v1.deps import _bad, _not_found, _ok
from backend.app.core.config import settings
from backend.app.core.oauth import SocialAuthError, verify_facebook_token, verify_google_id_token
from backend.app.core.password import hash_password, verify_password
from backend.app.core.security import (
    AUTH_COOKIE,
    _bearer_token_from_request,
    clear_login_failures,
    create_session,
    destroy_session,
    get_current_user,
    login_allowed,
    refresh_session,
    register_login_failure,
    require_json_auth,
    revoke_user_sessions,
)
from backend.app.db.connection import get_db
from backend.app.db.queries.users import (
    create_or_link_social_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_verify_token,
    register_user,
    update_user,
    verify_email,
)
from backend.app.schemas.api_v1 import (
    AuthMe,
    ChangePasswordResult,
    Data,
    LoginResult,
    LogoutResult,
    RegisterResponse,
    SessionRefreshResult,
)

router = APIRouter(prefix="/api/v1")


def _client_ip(request: Request) -> str:
    forwarded = getattr(request, "headers", {}).get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if getattr(request, "client", None):
        return request.client.host
    return "unknown"


def _user_public(user: dict) -> dict:
    """The user payload shared by login / social login / me."""
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "fleet_id": user.get("fleet_id"),
        "auth_provider": user.get("auth_provider") or "local",
        "email_verified": user.get("email_verified", True),
        "full_name": user.get("full_name", ""),
    }


@router.post("/auth/login", response_model=LoginResult)
async def api_auth_login(request: Request, response: Response):
    """Authenticate and return a Bearer token + user as JSON."""
    ip = _client_ip(request)
    body = {}
    if "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
    else:
        try:
            form = await request.form()
            body = {k: v for k, v in form.items()}
        except Exception:  # noqa: BLE001
            body = {}
    email = str(body.get("email", body.get("username", ""))).strip()  # back-compat: accept "username" key from old clients
    password = str(body.get("password", ""))

    allowed, lock_remaining = login_allowed(ip)
    if not allowed:
        return JSONResponse(status_code=423, content={"error": "locked", "code": "LOCKED", "retry_after_seconds": lock_remaining})
    with get_db() as conn:
        user = get_user_by_email(conn, email)
    if user is None or not verify_password(password, user["password_hash"]):
        remaining = register_login_failure(ip)
        return JSONResponse(status_code=401, content={"error": "invalid_credentials", "code": "INVALID_CREDENTIALS", "attempts_remaining": remaining})
    if not user["is_active"]:
        return JSONResponse(
            status_code=403,
            content={"error": "inactive", "code": "INACTIVE_ACCOUNT"},
        )
    # Block login if local account hasn't verified email yet.
    if (user.get("auth_provider") or "local") == "local" and not user.get("email_verified", True):
        return JSONResponse(
            status_code=403,
            content={
                "error": "email not verified",
                "code": "EMAIL_UNVERIFIED",
                "email": user.get("email"),
            },
        )
    clear_login_failures(ip)
    token = create_session(user["id"], user["email"], user["role"])
    landing = {
        "super_admin": "/dashboard",
        "trip_manager": "/dashboard",
        "driver": "/dashboard",
    }.get(user["role"], "/dashboard")
    if settings.auth_cookie_enabled:
        response.set_cookie(
            key=AUTH_COOKIE,
            value=token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.session_ttl_hours * 3600,
        )
    return {
        "token": token,
        "user": _user_public(user),
        "landing": landing,
    }


@router.get("/auth/me", response_model=AuthMe)
def api_auth_me(request: Request):
    """Return the current session user + expiry (audit E-10), or 401."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    session = get_current_user(request)
    # Fetch the full user row for email, fleet_id, etc.
    with get_db() as conn:
        db_user = get_user_by_id(conn, session["user_id"])
    user = _user_public(db_user) if db_user else {
        "id": session["user_id"],
        "role": session["role"],
    }
    return {
        "user": user,
        "expires_at": int(session.get("expires_at") or 0) or None,
    }


@router.post("/auth/refresh", response_model=Data[SessionRefreshResult])
def api_auth_refresh(request: Request, response: Response):
    """Sliding renewal (audit E-10): extend the caller's session TTL.

    Called by the SPA when the session enters its warning window. Rotates the
    auth cookie too when cookie issuance is enabled.
    """
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    token = request.cookies.get(AUTH_COOKIE) or _bearer_token_from_request(request)
    expires_at = refresh_session(token)
    if expires_at is None:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "code": "UNAUTHORIZED"},
        )
    if settings.auth_cookie_enabled:
        response.set_cookie(
            key=AUTH_COOKIE,
            value=token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.session_ttl_hours * 3600,
        )
    return _ok({"expires_at": expires_at})


def _social_login_response(response: Response, user: dict) -> JSONResponse:
    """Issue a standard VahanKhata session for a verified social user."""
    token = create_session(user["id"], user["email"], user["role"])
    if settings.auth_cookie_enabled:
        response.set_cookie(
            key=AUTH_COOKIE,
            value=token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.session_ttl_hours * 3600,
        )
    return JSONResponse(
        content={
            "token": token,
            "user": _user_public(user),
            "landing": "/dashboard",
        }
    )


@router.post("/auth/google", response_model=LoginResult)
async def api_auth_google(request: Request, response: Response):
    """Sign in / sign up with a Google ID token (from Google Identity Services)."""
    if not settings.google_client_id:
        return JSONResponse(
            status_code=503,
            content={"error": "google login disabled", "code": "PROVIDER_DISABLED"},
        )
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    try:
        identity = verify_google_id_token(str(body.get("credential", "")))
    except SocialAuthError as exc:
        return JSONResponse(
            status_code=401,
            content={"error": str(exc), "code": "SOCIAL_AUTH_FAILED"},
        )
    with get_db() as conn:
        user, _created = create_or_link_social_user(
            conn, "google", identity["sub"], identity["email"],
            identity["name"], settings.social_default_role,
        )
    if not user or not user["is_active"]:
        return JSONResponse(
            status_code=403,
            content={"error": "inactive", "code": "INACTIVE_ACCOUNT"},
        )
    return _social_login_response(response, user)


@router.post("/auth/facebook", response_model=LoginResult)
async def api_auth_facebook(request: Request, response: Response):
    """Sign in / sign up with a Facebook access token (from FB Login SDK)."""
    if not settings.facebook_app_id or not settings.facebook_app_secret:
        return JSONResponse(
            status_code=503,
            content={"error": "facebook login disabled", "code": "PROVIDER_DISABLED"},
        )
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    try:
        identity = verify_facebook_token(str(body.get("access_token", "")))
    except SocialAuthError as exc:
        return JSONResponse(
            status_code=401,
            content={"error": str(exc), "code": "SOCIAL_AUTH_FAILED"},
        )
    with get_db() as conn:
        user, _created = create_or_link_social_user(
            conn, "facebook", identity["sub"], identity["email"],
            identity["name"], settings.social_default_role,
        )
    if not user or not user["is_active"]:
        return JSONResponse(
            status_code=403,
            content={"error": "inactive", "code": "INACTIVE_ACCOUNT"},
        )
    return _social_login_response(response, user)


@router.post("/auth/logout", response_model=Data[LogoutResult])
def api_auth_logout(request: Request):
    destroy_session(request)
    return _ok({"logged_out": True})



@router.post("/auth/register", response_model=Data[RegisterResponse])
async def api_register(request: Request):
    """Create a new local user account with email verification."""
    try:
        body = await request.json()
    except Exception:
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")

    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    confirm_password = str(body.get("confirm_password", ""))

    if not email or "@" not in email:
        return _bad("valid email is required", "INVALID_EMAIL")
    if not password or len(password) < 8:
        return _bad("password must be at least 8 characters", "WEAK_PASSWORD")
    if password != confirm_password:
        return _bad("passwords do not match", "PASSWORD_MISMATCH")

    # Auto-derive display name from the email local-part.
    full_name = email.split("@", 1)[0].replace(".", " ").replace("_", " ").title() or email
    password_hash = hash_password(password)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = time.time() + (24 * 3600)

    try:
        with get_db() as conn:
            dup = conn.cursor().execute(
                "SELECT id FROM users WHERE lower(email) = %s", (email,)
            ).fetchone()
            if dup:
                return _bad("email already registered", "EMAIL_TAKEN")
            register_user(
                conn,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                phone=None,
                email_verify_token=token_hash,
                email_verify_expires_at=expires_at,
            )
    except Exception as e:
        return _bad(f"cannot register: {e}", "DUPLICATE_FIELD")

    from backend.app.services.email.client import send_verification_email_sync
    verify_url = f"{settings.app_public_url or 'http://localhost:5173'}/verify-email?token={raw_token}"
    send_verification_email_sync(
        to_email=email,
        full_name=full_name,
        verify_url=verify_url,
    )

    return _ok({"message": "registration successful - check your email to verify"})


@router.get("/auth/verify-email")
async def api_verify_email(token: str):
    """Confirm an email verification token, then redirect to the login page.

    GET /api/v1/auth/verify-email?token=...
    Redirects to the SPA root with a query flag so the login page can show a
    success or error message inline.
    """
    base = (settings.app_public_url or "").rstrip("/") or "/"
    if not token:
        return RedirectResponse(f"{base}/?verified=missing")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_db() as conn:
        user = get_user_by_verify_token(conn, token_hash)
        if not user:
            return RedirectResponse(f"{base}/?verified=invalid")
        verify_email(conn, user["id"])
    return RedirectResponse(f"{base}/?verified=1")


@router.post(
    "/auth/change-password", response_model=Data[ChangePasswordResult]
)
async def api_change_password(request: Request):
    """Verify the current password and set a new one for the logged-in user."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")

    current_password = str(body.get("current_password", ""))
    new_password = str(body.get("new_password", ""))
    confirm_password = str(body.get("confirm_password", ""))

    if not new_password or len(new_password) < 4:
        return _bad("new password must be at least 4 characters", "WEAK_PASSWORD")
    if new_password != confirm_password:
        return _bad(
            "new password and confirm password do not match", "PASSWORD_MISMATCH"
        )

    user = get_current_user(request)
    with get_db() as conn:
        db_user = get_user_by_id(conn, user.get("user_id"))
    if not db_user:
        return _not_found("user not found")
    if not verify_password(current_password, db_user["password_hash"]):
        return _bad("current password is incorrect", "WRONG_PASSWORD")

    new_hash = hash_password(new_password)
    with get_db() as conn:
        update_user(
            conn,
            user["user_id"],
            db_user["full_name"],
            db_user["role"],
            db_user["phone"],
            db_user["email"],
            password_hash=new_hash,
        )

    # Audit B-1: every existing session for this user dies with the old
    # credential — including this device's. The SPA clears its local token and
    # returns to the login screen on success (ChangePassword.jsx).
    revoke_user_sessions(user["user_id"])

    return _ok({"id": user["user_id"], "password_changed": True})
