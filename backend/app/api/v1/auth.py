"""Auth `/api/v1` router — login / me / logout / change-password.

Returns Bearer token + user as JSON (never a 303 redirect). Auth resolves via
cookie OR `Authorization: Bearer` through the shared in-memory session store.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.password import hash_password, verify_password
from backend.app.core.security import (
    AUTH_COOKIE,
    clear_login_failures,
    create_session,
    destroy_session,
    login_allowed,
    register_login_failure,
    require_json_auth,
    get_current_user,
)
from backend.app.db.connection import get_db
from backend.app.db.queries.users import get_user_by_id, get_user_by_username, update_user

from backend.app.api.v1.deps import _bad, _not_found, _ok
from backend.app.schemas.api_v1 import (
    AuthMe,
    ChangePasswordResult,
    Data,
    LoginResult,
    LogoutResult,
)

router = APIRouter(prefix="/api/v1")


def _client_ip(request: Request) -> str:
    forwarded = getattr(request, "headers", {}).get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if getattr(request, "client", None):
        return request.client.host
    return "unknown"


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
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    allowed, lock_remaining = login_allowed(ip)
    if not allowed:
        return JSONResponse(
            status_code=423,
            content={
                "error": "locked",
                "code": "LOCKED",
                "retry_after_seconds": lock_remaining,
            },
        )
    with get_db() as conn:
        user = get_user_by_username(conn, username)
    if user is None or not verify_password(password, user["password_hash"]):
        remaining = register_login_failure(ip)
        return JSONResponse(
            status_code=401,
            content={
                "error": "invalid_credentials",
                "code": "INVALID_CREDENTIALS",
                "attempts_remaining": remaining,
            },
        )
    if not user["is_active"]:
        return JSONResponse(
            status_code=403,
            content={"error": "inactive", "code": "INACTIVE_ACCOUNT"},
        )
    clear_login_failures(ip)
    token = create_session(user["id"], user["username"], user["role"])
    landing = {
        "super_admin": "/dashboard",
        "trip_manager": "/dashboard",
        "driver": "/dashboard",
    }.get(user["role"], "/dashboard")
    response.set_cookie(
        key=AUTH_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    return {
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
        "landing": landing,
    }


@router.get("/auth/me", response_model=AuthMe)
def api_auth_me(request: Request):
    """Return the current session user (cookie or Bearer) as JSON, or 401."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = get_current_user(request)
    return {
        "user": {"id": user["user_id"], "username": user["username"], "role": user["role"]},
    }


@router.post("/auth/logout", response_model=Data[LogoutResult])
def api_auth_logout(request: Request):
    destroy_session(request)
    return _ok({"logged_out": True})


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

    return _ok({"id": user["user_id"], "password_changed": True})