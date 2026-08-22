from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import _bad, _created, _identity, _not_found, _ok
from backend.app.core.security import require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.trip_templates import (
    delete_template,
    insert_template,
    list_for_fleet,
)
from backend.app.db.queries.users import get_user_fleet_id
from backend.app.schemas.api_v1 import Data, ResourceAck

router = APIRouter(prefix="/api/v1")


@router.get("/trip-templates", response_model=Data[list[dict]])
def api_list_trip_templates(request: Request):
    """Fleet-scoped reusable routes (feature F-6)."""
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        fleet_id = get_user_fleet_id(conn, _identity(request).get("user_id"))
        if fleet_id is None:
            return _bad("no fleet configured for this user", "NO_FLEET")
        templates = list_for_fleet(conn, fleet_id)
    return _ok(templates)


@router.post("/trip-templates", response_model=Data[ResourceAck])
async def api_create_trip_template(request: Request):
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
    name = str(body.get("name", "")).strip()
    if not name:
        return _bad("name is required", "MISSING_FIELDS")

    def _opt(key):
        raw = body.get(key)
        return int(raw) if raw not in (None, "", 0, "0") else None

    with get_db() as conn:
        fleet_id = get_user_fleet_id(conn, user.get("user_id"))
        if fleet_id is None:
            return _bad("no fleet configured for this user", "NO_FLEET")
        new_id = insert_template(
            conn,
            fleet_id=fleet_id,
            name=name[:80],
            vehicle_id=_opt("vehicle_id"),
            driver_user_id=_opt("driver_user_id"),
            origin=(str(body.get("origin") or "").strip() or None)[:100] if body.get("origin") else None,
            destination=(str(body.get("destination") or "").strip() or None)[:100] if body.get("destination") else None,
            created_by=user.get("user_id"),
        )
    return _created({"id": new_id})


@router.delete("/trip-templates/{tid}")
def api_delete_trip_template(request: Request, tid: int):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        fleet_id = get_user_fleet_id(conn, _identity(request).get("user_id"))
        if fleet_id is None:
            return _bad("no fleet configured for this user", "NO_FLEET")
        ok = delete_template(conn, tid, fleet_id)
    if not ok:
        return _not_found("template not found")
    return _ok({"id": tid, "deleted": True})
