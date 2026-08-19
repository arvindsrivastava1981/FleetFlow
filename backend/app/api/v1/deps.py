"""Shared HTTP helpers for the `/api/v1` sub-routers.

Centralizes the serialization and response helpers that every domain router
would otherwise duplicate:

- ``_jsonable``: recursively coerce psycopg2 rows (dates, dicts, lists) to
  JSON-safe primitives.
- ``_ok`` / ``_created``: success envelopes (`{ "data": ... }`).
- ``_bad`` / ``_not_found``: JSONError responses with a stable error ``code``.
- ``_identity`` / ``get_current_user`` import: auth identity access.
- ``_trip_forbidden``: multi-tenant (fleet) authorization for a trip row.
- ``_read_json_body``: safely parse a JSON request body (falls back to {}).

Routers must use ``router = APIRouter(prefix="/api/v1")`` locally; this module
does NOT declare a prefix so it can be imported by any sub-router without
stacking prefixes.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.app.core.security import get_current_user
from backend.app.db.queries.users import get_user_fleet_id


def _jsonable(value: Any) -> Any:
    """Recursively coerce psycopg2 rows into JSON-safe primitives."""
    if isinstance(value, _dt.datetime):
        return value.isoformat(sep=" ", timespec="minutes")
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _ok(payload: Any) -> dict:
    """`{ "data": <payload> }` envelope; lets FastAPI apply response_model."""
    return {"data": _jsonable(payload)}


def _created(payload: Any) -> dict:
    """`{ "data": <payload> }` envelope for 201 Created responses."""
    return {"data": _jsonable(payload)}


def _bad(msg: str, code: str = "BAD_REQUEST") -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": msg, "code": code})


def _not_found(msg: str = "not found") -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": msg, "code": "NOT_FOUND"})


def _identity(request: Request) -> dict:
    return get_current_user(request) or {}


def _trip_forbidden(conn, user: dict, trip: dict) -> bool:
    """Multi-tenant (fleet) authorization for a trip row.

    super_admin may access any fleet's trips. Every other role must be bound to
    the trip on the tenant dimension (fleet_id) in addition to their ownership:
      - trip_manager: must have created the trip AND belong to the trip's fleet.
      - driver: must be the assigned driver AND belong to the trip's fleet.
    Returns True when access must be forbidden (the caller has no right to it).
    """
    role = user.get("role", "")
    uid = user.get("user_id")
    if role == "super_admin":
        return False
    if role == "trip_manager":
        if trip.get("created_by") != uid:
            return True
    elif role == "driver":
        if trip.get("driver_user_id") != uid:
            return True
    else:
        return True
    # Fleet-level (tenant) equality: a user scoped to a fleet may only read or
    # mutate trips that belong to that same fleet.
    user_fleet = get_user_fleet_id(conn, uid) if uid else None
    if user_fleet is not None and trip.get("fleet_id") not in (None, user_fleet):
        return True
    return False


async def _read_json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return {}
    return body if isinstance(body, dict) else {}