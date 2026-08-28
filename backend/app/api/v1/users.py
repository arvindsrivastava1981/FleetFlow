from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import (
    _bad,
    _created,
    _identity,
    _not_found,
    _ok,
    _page_params,
)
from backend.app.core.config import settings
from backend.app.core.password import hash_password
from backend.app.core.security import require_json_role, revoke_user_sessions
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    get_default_fleet,
    get_fleet_by_id,
    get_fleet_email_context,
    get_fleet_entitlement,
    is_trial_active,
    start_trial_subscription,
)
from backend.app.db.queries.users import (
    create_user,
    deactivate_user,
    get_all_users,
    get_drivers_for_user,
    get_user_by_id,
    reactivate_user,
    update_user,
)
from backend.app.schemas.api_v1 import Data, ResourceAck, ToggleAck
from backend.app.services.email.client import (
    manager_onboarding_email_context,
    send_manager_onboarding_email_sync,
)

router = APIRouter(prefix="/api/v1")

VALID_ROLES: tuple[str, ...] = ("super_admin", "trip_manager", "driver")


def _resolve_user_fleet(conn) -> dict | None:
    """Resolve the fleet a freshly-created trip manager belongs to."""
    default = get_default_fleet(conn)
    if default is None:
        return None
    return get_fleet_email_context(conn, default["id"])


def _resolve_default_fleet_id(conn) -> int | None:
    """Return the default active fleet id for binding a new trip manager."""
    default = get_default_fleet(conn)
    return default["id"] if default else None


def _fleet_entitled(conn, fleet_id: int) -> bool:
    """True when a fleet can currently register vehicles (active or trial)."""
    entitlement = get_fleet_entitlement(conn, fleet_id)
    if not entitlement:
        return False
    return entitlement["subscription_status"] == "ACTIVE" or is_trial_active(
        conn, fleet_id
    )


def _login_url(request: Request) -> str:
    base = (settings.app_public_url or "").strip().rstrip("/")
    if not base:
        base = str(request.base_url).rstrip("/")
    return f"{base}/"


def _manager_onboarding_payload(
    conn, new_id: int, full_name: str, temporary_password: str,
    manager_email: str | None, request: Request,
) -> dict | None:
    """Build the manager onboarding email kwargs, or None if it can't be sent."""
    if not temporary_password:
        return None
    manager_email = (manager_email or "").strip()
    if not manager_email:
        return None
    fleet = _resolve_user_fleet(conn)
    if fleet is None:
        return None
    user = get_user_by_id(conn, new_id)
    display_name = (user or {}).get("full_name") or full_name
    ctx = manager_onboarding_email_context(
        manager_full_name=display_name,
        manager_username=manager_email,
        temporary_password=temporary_password,
        fleet=fleet,
        login_url=_login_url(request),
    )
    ctx["to_email"] = manager_email
    return ctx


@router.get("/users", response_model=Data[list[dict[str, Any]]])
def api_users(request: Request):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    limit, offset = _page_params(request)  # audit R-7
    with get_db() as conn:
        users = get_all_users(conn, limit=limit, offset=offset)
    for u in users:
        u.pop("password_hash", None)
    return _ok(users)


@router.post("/users", response_model=Data[ResourceAck])
async def api_create_user(request: Request):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    email = str(body.get("email", body.get("username", ""))).strip()
    full_name = str(body.get("full_name", "")).strip()
    role = str(body.get("role", ""))
    password = str(body.get("password", ""))
    if role not in VALID_ROLES or not password or not email:
        return _bad("invalid role, missing password or email", "VALIDATION")
    phone = (body.get("phone") or "").strip() or None
    batta_type = (body.get("batta_type") or "").strip() or None
    default_batta_rate = body.get("default_batta_rate")
    if role != "driver":
        batta_type = None
        default_batta_rate = None
    # Fleet picker (G1): allow a Super Admin to target a non-default fleet when
    # creating a trip_manager. Falls back to the default active fleet when absent.
    requested_fleet_id = body.get("fleet_id")
    with get_db() as conn:
        # Bind a new Trip Manager to the default active fleet so vehicle
        # creation resolves to a valid, billable fleet (get_user_fleet_id).
        if role == "trip_manager":
            manager_fleet_id = int(requested_fleet_id) if requested_fleet_id else None
            if manager_fleet_id is None:
                manager_fleet_id = _resolve_default_fleet_id(conn)
            elif get_fleet_by_id(conn, manager_fleet_id) is None:
                return _bad("unknown fleet_id", "INVALID_FLEET")
            if manager_fleet_id is not None and not _fleet_entitled(conn, manager_fleet_id):
                # Seed/default fleets may be TRIAL with no trial clock set
                # (treated as expired). Start the 15-day trial so the new
                # manager can immediately register their first vehicle.
                start_trial_subscription(conn, manager_fleet_id)
        else:
            manager_fleet_id = None
        new_id = create_user(
            conn, email, hash_password(password), full_name, role,
            phone, created_by=user.get("user_id"),
            fleet_id=manager_fleet_id,
            batta_type=batta_type,
            default_batta_rate=default_batta_rate,
        )
        if role == "trip_manager":
            ctx = _manager_onboarding_payload(
                conn, new_id, full_name, password, email, request
            )
            if ctx is not None:
                send_manager_onboarding_email_sync(**ctx)
    return _created({"id": new_id})


@router.put("/users/{uid}", response_model=Data[ResourceAck])
async def api_update_user(request: Request, uid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    role = str(body.get("role", ""))
    if role not in VALID_ROLES:
        return _bad("invalid role", "VALIDATION")
    full_name = str(body.get("full_name", "")).strip()
    phone = (body.get("phone") or "").strip() or None
    email = (body.get("email") or "").strip() or None
    password = body.get("password") or None
    pw_hash = hash_password(password) if password else None
    batta_type = (body.get("batta_type") or "").strip() or None
    default_batta_rate = body.get("default_batta_rate")
    if role != "driver":
        batta_type = None
        default_batta_rate = None
    with get_db() as conn:
        ok = update_user(
            conn, uid, full_name, role, phone, email, password_hash=pw_hash,
            batta_type=batta_type, default_batta_rate=default_batta_rate,
        )
    if not ok:
        return _not_found("user not found")
    return _ok({"id": uid})


@router.post("/users/{uid}/toggle", response_model=Data[ToggleAck])
async def api_toggle_user(request: Request, uid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    should_activate = bool((body or {}).get("activate", False))
    with get_db() as conn:
        existing = get_user_by_id(conn, uid)
        if existing is None:
            return _not_found("user not found")
        if should_activate:
            reactivate_user(conn, uid)
        else:
            deactivate_user(conn, uid)
            # Audit B-1: a deactivated account must lose live access NOW,
            # not when its (up to 72 h) session TTL expires.
            revoke_user_sessions(uid)
    return _ok({"id": uid, "is_active": should_activate})
# ---- Drivers (Trip Manager / Super Admin) ----------------------------------


@router.get("/drivers", response_model=Data[list[dict[str, Any]]])
def api_drivers(request: Request):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    limit, offset = _page_params(request)  # audit R-7
    with get_db() as conn:
        # Ownership scoping: a trip_manager lists only drivers they created;
        # super_admin sees all. Never expose one manager's drivers to another.
        drivers = get_drivers_for_user(
            conn,
            role=user.get("role", "super_admin"),
            user_id=user.get("user_id"),
            limit=limit,
            offset=offset,
        )
    for d in drivers:
        d.pop("password_hash", None)
    return _ok(drivers)


@router.post("/drivers", response_model=Data[ResourceAck])
async def api_create_driver(request: Request):
    """Create a driver user (Trip Manager / Super Admin), with batta profile."""
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    email = str(body.get("email", body.get("username", ""))).strip()
    full_name = str(body.get("full_name", "")).strip()
    password = str(body.get("password", ""))
    if not email or not full_name or not password:
        return _bad("email, full_name and password are required", "MISSING_FIELDS")
    phone = (body.get("phone") or "").strip() or None
    batta_type = (body.get("batta_type") or "").strip() or None
    default_batta_rate = body.get("default_batta_rate")
    with get_db() as conn:
        new_id = create_user(
            conn, email, hash_password(password), full_name, "driver",
            phone, created_by=user.get("user_id"),
            batta_type=batta_type,
            default_batta_rate=default_batta_rate,
        )
    return _created({"id": new_id})


@router.put("/drivers/{uid}", response_model=Data[ResourceAck])
async def api_update_driver(request: Request, uid: int):
    """Update a driver's profile / batta (Trip Manager / Super Admin)."""
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    full_name = str(body.get("full_name", "")).strip()
    if not full_name:
        return _bad("full_name is required", "MISSING_FIELDS")
    phone = (body.get("phone") or "").strip() or None
    email = (body.get("email") or "").strip() or None
    password = body.get("password") or None
    pw_hash = hash_password(password) if password else None
    batta_type = (body.get("batta_type") or "").strip() or None
    default_batta_rate = body.get("default_batta_rate")
    licence_raw = str(body.get("licence_expiry") or "").strip() or None  # audit P-5
    if licence_raw is not None:
        try:
            licence_dt = date.fromisoformat(licence_raw)
        except ValueError:
            return _bad("invalid licence_expiry (use YYYY-MM-DD)", "INVALID_DATE")
    else:
        licence_dt = None
    with get_db() as conn:
        existing = get_user_by_id(conn, uid)
        if existing is None or existing.get("role") != "driver":
            return _not_found("driver not found")
        # Ownership: a manager may only edit drivers they created (404 — not
        # 403 — so the driver's existence is not leaked cross-manager).
        if (
            user.get("role") != "super_admin"
            and existing.get("created_by") != user.get("user_id")
        ):
            return _not_found("driver not found")
        ok = update_user(
            conn, uid, full_name, "driver", phone, email, password_hash=pw_hash,
            batta_type=batta_type, default_batta_rate=default_batta_rate,
        )
        if licence_dt is not None:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET licence_expiry = %s WHERE id = %s",
                (licence_dt, uid),
            )
    if not ok:
        return _not_found("driver not found")
    return _ok({"id": uid})


@router.post("/drivers/{uid}/toggle", response_model=Data[ToggleAck])
async def api_toggle_driver(request: Request, uid: int):
    """Activate / deactivate a driver (Trip Manager / Super Admin)."""
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    should_activate = bool((body or {}).get("activate", False))
    with get_db() as conn:
        existing = get_user_by_id(conn, uid)
        if existing is None or existing.get("role") != "driver":
            return _not_found("driver not found")
        # Ownership: a manager cannot activate/deactivate another manager's
        # driver (404 — existence not leaked cross-manager).
        if (
            user.get("role") != "super_admin"
            and existing.get("created_by") != user.get("user_id")
        ):
            return _not_found("driver not found")
        if should_activate:
            reactivate_user(conn, uid)
        else:
            deactivate_user(conn, uid)
            # Audit B-1: deactivation kills live sessions immediately.
            revoke_user_sessions(uid)
    return _ok({"id": uid, "is_active": should_activate})
