from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    get_default_fleet,
    get_fleet_entitlement,
)
from backend.app.db.queries.users import get_user_fleet_id
from backend.app.db.queries.vehicles import (
    deactivate_vehicle,
    get_all_vehicles,
    insert_vehicle,
    reactivate_vehicle,
    update_vehicle,
    vehicle_number_exists,
)

from backend.app.api.v1.deps import _bad, _created, _identity, _not_found, _ok
from backend.app.schemas.api_v1 import Data, ResourceAck, ToggleAck
from backend.app.services.entitlements import fleet_can_add_vehicles

import re as _re

router = APIRouter(prefix="/api/v1")
_PLATE_RE = _re.compile(settings.plate_regex)


def _resolve_vehicle_fleet(conn, user: dict) -> int | None:
    """Resolve the fleet a new vehicle belongs to (mirrors vehicles.py flow)."""
    fleet_id = (
        get_user_fleet_id(conn, user.get("user_id")) if user.get("user_id") else None
    )
    if fleet_id is None:
        default = get_default_fleet(conn)
        if default:
            fleet_id = default["id"]
    return fleet_id


@router.get("/vehicles", response_model=Data[list[dict[str, Any]]])
def api_vehicles(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    with get_db() as conn:
        vehicles = get_all_vehicles(
            conn, role=user.get("role", "super_admin"), user_id=user.get("user_id")
        )
    return _ok(vehicles)


@router.post("/vehicles", response_model=Data[ResourceAck])
async def api_create_vehicle(request: Request):
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
    number = str(body.get("vehicle_number", "")).strip().upper()
    if not _PLATE_RE.match(number):
        return _bad("invalid license plate", "INVALID_PLATE")
    make_model = (body.get("make_model") or "").strip() or None
    tank_capacity_liters = float(body.get("tank_capacity_liters", 350.0))
    expected_km_per_liter = float(body.get("expected_km_per_liter", 4.0))
    owner_phone = (body.get("owner_phone") or "").strip() or None

    with get_db() as conn:
        if vehicle_number_exists(conn, number):
            return _bad("vehicle number already exists", "DUP_VEHICLE")
        fleet_id = _resolve_vehicle_fleet(conn, user)
        if fleet_id is None:
            return _bad("no fleet configured for this user", "NO_FLEET")
        entitlement = get_fleet_entitlement(conn, fleet_id)
        allowed, reason = fleet_can_add_vehicles(conn, fleet_id, entitlement)
        if not allowed:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "vehicle limit reached for this fleet",
                    "code": "VEHICLE_LIMIT" if reason == "VEHICLE_LIMIT" else "NOT_ENTITLED",
                },
            )
        new_id = insert_vehicle(
            conn, number, make_model, tank_capacity_liters, expected_km_per_liter,
            owner_phone, created_by=user.get("user_id"), fleet_id=fleet_id,
        )
    return _created({"id": new_id})


@router.put("/vehicles/{vid}", response_model=Data[ResourceAck])
async def api_update_vehicle(request: Request, vid: int):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    number = str(body.get("vehicle_number", "")).strip().upper()
    if not _PLATE_RE.match(number):
        return _bad("invalid license plate", "INVALID_PLATE")
    make_model = (body.get("make_model") or "").strip() or None
    tank_capacity_liters = float(body.get("tank_capacity_liters", 350.0))
    expected_km_per_liter = float(body.get("expected_km_per_liter", 4.0))
    owner_phone = (body.get("owner_phone") or "").strip() or None

    with get_db() as conn:
        if vehicle_number_exists(conn, number, exclude_id=vid):
            return _bad("vehicle number already exists", "DUP_VEHICLE")
        ok = update_vehicle(
            conn, vid, number, make_model, tank_capacity_liters,
            expected_km_per_liter, owner_phone,
        )
    if not ok:
        return _not_found("vehicle not found")
    return _ok({"id": vid})


@router.post("/vehicles/{vid}/toggle", response_model=Data[ToggleAck])
async def api_toggle_vehicle(request: Request, vid: int):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    should_activate = bool((body or {}).get("activate", False))
    with get_db() as conn:
        if should_activate:
            reactivate_vehicle(conn, vid)
        else:
            deactivate_vehicle(conn, vid)
    return _ok({"id": vid, "is_active": should_activate})