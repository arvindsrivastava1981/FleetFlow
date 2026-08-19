"""Fleet CRUD `/api/v1` router (Super Admin).

Manages fleets and the plan catalogue listing. Plan upgrades / vehicle-slot
purchases live in the billing router; this router only owns the fleet entity
(list, plans, create, update, toggle).
"""
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
    get_fleet_by_id,
    insert_fleet,
    reactivate_fleet,
    update_fleet,
)

from backend.app.api.v1.deps import _bad, _created, _not_found, _ok
from backend.app.schemas.api_v1 import Data, ResourceAck, ToggleAck

router = APIRouter(prefix="/api/v1")


@router.get("/fleets", response_model=Data[list[dict[str, Any]]])
def api_get_fleets(request: Request):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        fleets = get_all_fleets(conn)
    return _ok(fleets)


@router.get("/fleets/plans", response_model=Data[list[dict[str, Any]]])
def api_get_plans(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    with get_db() as conn:
        plans = get_all_plans(conn)
    return _ok(plans)


@router.post("/fleets", response_model=Data[ResourceAck])
async def api_create_fleet(request: Request):
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