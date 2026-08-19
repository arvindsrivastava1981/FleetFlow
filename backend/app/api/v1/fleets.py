from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    deactivate_fleet,
    fleet_phone_exists,
    get_all_fleets,
    get_all_plans,
    get_fleet_billing_events,
    get_fleet_by_id,
    insert_fleet,
    log_fleet_billing_event,
    reactivate_fleet,
    start_trial_subscription,
    update_fleet,
)
from backend.app.db.queries.users import update_user as _update_user_row

from backend.app.api.v1.deps import _bad, _created, _identity, _not_found, _ok
from backend.app.db.queries.users import get_user_fleet_id
from backend.app.schemas.api_v1 import Data, ResourceAck, ToggleAck

router = APIRouter(prefix="/api/v1")


@router.get("/fleets", response_model=Data[list[dict[str, Any]]])
def api_get_fleets(request: Request):
    guard = require_json_role(request, "super_admin", "trip_manager")
    if guard is not None:
        return guard
    user = _identity(request)
    role = user.get("role", "super_admin")
    with get_db() as conn:
        if role == "super_admin":
            fleets = get_all_fleets(conn)
        else:
            fleet_id = get_user_fleet_id(conn, user.get("user_id"))
            fleets = get_all_fleets(conn, fleet_id)
    return _ok(fleets)


@router.get("/fleets/plans", response_model=Data[list[dict[str, Any]]])
def api_get_plans(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    with get_db() as conn:
        plans = get_all_plans(conn)
    return _ok(plans)


@router.get("/fleets/{fid}/billing", response_model=Data[dict[str, Any]])
def api_fleet_billing_health(request: Request, fid: int):
    """Super Admin per-fleet billing/entitlement health panel (G6).

    Returns subscription state, effective limits, and the audit ledger.
    """
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    from backend.app.db.queries.fleets import (
        count_active_vehicles,
        get_fleet_entitlement,
    )
    from backend.app.services.entitlements import fleet_feature

    with get_db() as conn:
        fleet = get_fleet_by_id(conn, fid)
        if fleet is None:
            return _not_found("fleet not found")
        ent = get_fleet_entitlement(conn, fid)
        vehicle_count = count_active_vehicles(conn, fid)
        events = get_fleet_billing_events(conn, fid)
        effective_limit = fleet_feature(conn, fid, "vehicle_limit")
    return _ok(
        {
            "fleet_id": fid,
            "owner_name": fleet.get("owner_name"),
            "subscription_status": (ent or {}).get("subscription_status"),
            "plan_code": (ent or {}).get("plan_code"),
            "vehicle_count": vehicle_count,
            "vehicle_limit": effective_limit,
            "used_slots": vehicle_count,
            "entitlement_addons": fleet.get("entitlement_addons"),
            "trial_ends_at": fleet.get("trial_ends_at"),
            "next_billing_date": fleet.get("next_billing_date"),
            "events": events,
        }
    )


@router.post("/fleets", response_model=Data[ResourceAck])
async def api_create_fleet(request: Request):
    guard = require_json_role(request, "super_admin", "trip_manager")
    if guard is not None:
        return guard
    user = _identity(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    owner_name = str(body.get("owner_name", "")).strip()
    phone = str(body.get("phone", "")).strip()
    email = body.get("email") or None
    plan = str(body.get("subscription_plan", "MONTHLY")).upper()
    if not owner_name or not phone:
        return _bad("owner_name and phone are required", "MISSING_FIELDS")
    with get_db() as conn:
        if fleet_phone_exists(conn, phone):
            return JSONResponse(
                status_code=409,
                content={"error": "fleet with this phone exists", "code": "DUP_PHONE"},
            )
        new_id = insert_fleet(
            conn, owner_name, phone, email.strip() if email else None, plan
        )
        # In-place switch: when a trip_manager creates a fleet, it becomes
        # their active fleet so vehicles they create resolve into it
        # (get_user_fleet_id), and billing/trips follow the same tenant.
        role = user.get("role", "super_admin")
        uid = user.get("user_id")
        if role == "trip_manager" and uid is not None:
            _update_user_row(conn, uid, None, None, fleet_id=new_id)
    return _created({"id": new_id})


@router.put("/fleets/{fid}", response_model=Data[ResourceAck])
async def api_update_fleet(request: Request, fid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    owner_name = str(body.get("owner_name", "")).strip()
    phone = str(body.get("phone", "")).strip()
    email = body.get("email") or None
    if not owner_name or not phone:
        return _bad("owner_name and phone are required", "MISSING_FIELDS")
    with get_db() as conn:
        if fleet_phone_exists(conn, phone, exclude_id=fid):
            return JSONResponse(
                status_code=409,
                content={"error": "fleet with this phone exists", "code": "DUP_PHONE"},
            )
        ok = update_fleet(conn, fid, owner_name, phone, email.strip() if email else None)
    if not ok:
        return _not_found("fleet not found")
    return _ok({"id": fid})


@router.post("/fleets/{fid}/toggle", response_model=Data[ToggleAck])
async def api_toggle_fleet(request: Request, fid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    should_activate = bool((body or {}).get("activate", False))
    with get_db() as conn:
        existing = get_fleet_by_id(conn, fid)
        if existing is None:
            return _not_found("fleet not found")
        if should_activate:
            reactivate_fleet(conn, fid)
        else:
            deactivate_fleet(conn, fid)
    return _ok({"id": fid, "is_active": should_activate})