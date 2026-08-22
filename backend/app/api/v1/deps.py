from __future__ import annotations

import datetime as _dt
from typing import Any

from fastapi import Request

from backend.app.core.errors import bad_request as _err_bad
from backend.app.core.errors import not_found as _err_not_found
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


def _page_params(
    request: Request, default_limit: int = 100, max_limit: int = 500
) -> tuple[int, int]:
    """Parse ``?limit=&offset=`` with clamps (audit R-7).

    Defaults keep responses byte-identical for existing clients; the cap
    bounds worst-case payloads on grown tables. Callers pass these straight
    into the list query fns' ``limit`` / ``offset`` parameters.
    """
    qp = request.query_params
    try:
        limit = int(qp.get("limit", default_limit))
    except (TypeError, ValueError):
        limit = default_limit
    try:
        offset = int(qp.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    return max(1, min(limit, max_limit)), max(0, offset)


def _bad(msg: str, code: str = "BAD_REQUEST") -> None:
    """Raise a 400 API error; the global handler logs it + returns JSON.

    This raises rather than returns so existing `return _bad(...)` call sites
    propagate the exception through FastAPI's global handlers unchanged.
    """
    raise _err_bad(msg, code=code)


def _not_found(msg: str = "not found") -> None:
    """Raise a 404 API error; the global handler logs it + returns JSON."""
    raise _err_not_found(msg)


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
