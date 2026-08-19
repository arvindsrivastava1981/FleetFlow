from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from backend.app.core.config import settings
from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.settlement import get_settled_trips
from backend.app.db.queries.trips import (
    active_trip_exists,
    get_trip_by_code,
    get_trip_stats_by_code,
    get_trips_for_user,
    insert_trip,
    pending_expense_count,
    settle_trip as mark_trip_settled,
)
from backend.app.db.queries.users import (
    get_driver_batta_profile,
    get_user_fleet_id,
)
from backend.app.db.queries.fleets import get_default_fleet
from backend.app.db.queries.expenses import get_expenses_for_trip
from backend.app.services.audit.cash import compute_settlement, resolve_trip_batta
from backend.app.services.pdf.settlement import build_settlement_pdf

from backend.app.api.v1.deps import (
    _bad,
    _created,
    _identity,
    _jsonable,
    _not_found,
    _ok,
    _trip_forbidden,
)
from backend.app.schemas.api_v1 import (
    CreateTripResult,
    Data,
    DriverSalary,
    SettleTripResult,
    TripDetailData,
    TripListItem,
)

import re as _re

router = APIRouter(prefix="/api/v1")
_PLATE_RE = _re.compile(settings.plate_regex)


def _resolve_trip_fleet(conn, user: dict) -> int | None:
    """Resolve the tenant fleet for a new trip (mirrors trips.py logic)."""
    fleet_id = (
        get_user_fleet_id(conn, user.get("user_id")) if user.get("user_id") else None
    )
    if fleet_id is None:
        default = get_default_fleet(conn)
        if default:
            fleet_id = default["id"]
    return fleet_id
@router.get("/trips", response_model=Data[list[TripListItem]])
def api_trips(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    role = user.get("role", "super_admin")
    user_id = user.get("user_id")

    with get_db() as conn:
        trips = get_trips_for_user(conn, user_id, role)
        stats = get_trip_stats_by_code(conn)
    for t in trips:
        t["stats"] = stats.get(t["trip_code"], {})
    return _ok(trips)


@router.get("/trips/{trip_code}", response_model=Data[TripDetailData])
def api_trip_detail(request: Request, trip_code: str):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    trip_code = trip_code.strip().upper()

    with get_db() as conn:
        trip = get_trip_by_code(conn, trip_code)
        if trip is None:
            return _not_found("trip not found")
        if _trip_forbidden(conn, user, trip):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        expenses = get_expenses_for_trip(conn, trip_code)
        res = compute_settlement(trip, expenses)
        trip["settlement"] = {
            "advance_amount": res.advance_amount,
            "goods_income": res.goods_income,
            "total_cr": res.total_cr,
            "expense_buckets": res.expense_buckets,
            "total_road_expenses": res.total_road_expenses,
            "driver_batta": res.driver_batta,
            "total_driver_credits": res.total_driver_credits,
            "net_balance": res.net_balance,
            "is_driver_refund": res.is_driver_refund,
            "status_label_en": res.status_label_en,
            "status_label_hi": res.status_label_hi,
            "avg_kml": res.avg_kml,
            "verification_hash": res.verification_hash,
        }

    return _ok({"trip": trip, "expenses": expenses})
@router.post("/trips", response_model=Data[CreateTripResult])
async def api_create_trip(request: Request):
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

    vehicle_no = str(body.get("vehicle_no", "")).strip().upper()
    driver_name = str(body.get("driver_name", "")).strip()
    driver_phone = str(body.get("driver_phone", "")).strip()
    advance_amount = float(body.get("advance_amount", 0.0))
    start_odo = float(body.get("start_odo", 0.0))
    vehicle_id = body.get("vehicle_id") or None
    driver_user_id = body.get("driver_user_id") or None

    if not vehicle_no or not driver_name:
        return _bad("vehicle_no and driver_name are required", "MISSING_FIELDS")
    if advance_amount < 0 or start_odo < 0:
        return _bad(
            "advance_amount and start_odo must be non-negative", "INVALID_NUMBER"
        )
    if not _PLATE_RE.match(vehicle_no):
        return _bad("invalid license plate", "INVALID_PLATE")
    digits = _re.sub(r"\D", "", driver_phone or "")
    if not (digits.startswith("91") and len(digits) == 12):
        return _bad("driver_phone must be a valid +91 number", "INVALID_PHONE")

    with get_db() as conn:
        fleet_id = _resolve_trip_fleet(conn, user)
        if fleet_id is None:
            return _bad("no fleet configured for this user", "NO_FLEET")
        if active_trip_exists(conn, fleet_id=fleet_id):
            return JSONResponse(
                status_code=409,
                content={
                    "error": "an active trip already exists for this fleet",
                    "code": "ACTIVE_TRIP_EXISTS",
                },
            )
        driver = get_driver_batta_profile(conn, driver_user_id)
        driver_batta_amount = resolve_trip_batta(driver)
        trip_code = insert_trip(
            conn,
            fleet_id,
            vehicle_no,
            driver_name,
            driver_phone,
            advance_amount,
            start_odo,
            created_by=user.get("user_id"),
            driver_user_id=driver_user_id,
            vehicle_id=vehicle_id,
            driver_batta_amount=driver_batta_amount,
        )
    return _created({"trip_code": trip_code, "status": "ACTIVE"})
@router.post("/trips/{trip_code}/settle", response_model=Data[SettleTripResult])
def api_settle_trip(request: Request, trip_code: str):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    trip_code = trip_code.strip().upper()

    with get_db() as conn:
        trip = get_trip_by_code(conn, trip_code)
        if trip is None:
            return _not_found("trip not found")
        if _trip_forbidden(conn, user, trip):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        if pending_expense_count(conn, trip_code):
            return JSONResponse(
                status_code=409,
                content={
                    "error": "cannot settle: pending expenses remain",
                    "code": "PENDING_EXPENSES",
                },
            )
        mark_trip_settled(conn, trip_code)
    return _ok({"trip_code": trip_code, "status": "SETTLED"})


@router.get("/settlements", response_model=Data[list[dict[str, Any]]])
def api_settled_trips(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    with get_db() as conn:
        trips = get_settled_trips(
            conn, role=user.get("role", "super_admin"), user_id=user.get("user_id")
        )
    return _ok(trips)


@router.get(
    "/settlements/{trip_code}/pdf", response_class=Response, response_model=None
)
def api_settlement_pdf(request: Request, trip_code: str):
    """Stream the settlement PDF (application/pdf) for a settled/completed trip."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    trip_code = trip_code.strip().upper()

    with get_db() as conn:
        trip = get_trip_by_code(conn, trip_code)
        if trip is None:
            return _not_found("trip not found")
        if _trip_forbidden(conn, user, trip):
            return Response("Forbidden", status_code=403)
        expenses = get_expenses_for_trip(conn, trip_code)

    pdf_bytes = build_settlement_pdf(trip, expenses)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={trip_code}_Settlement.pdf"
        },
    )


@router.get("/driver/salary", response_model=Data[DriverSalary])
def api_driver_salary(request: Request):
    """Read-only salary/batta summary for the logged-in driver."""
    guard = require_json_role(request, "driver")
    if guard is not None:
        return guard
    user = _identity(request)
    user_id = user.get("user_id")

    with get_db() as conn:
        profile = get_driver_batta_profile(conn, user_id) or {}
        trips = get_trips_for_user(conn, user_id, "driver")
        rows: list[dict] = []
        for t in trips:
            expenses = get_expenses_for_trip(conn, t["trip_code"])
            res = compute_settlement(t, expenses)
            rows.append(
                {
                    "trip_code": t["trip_code"],
                    "vehicle_no": t.get("vehicle_no"),
                    "origin": t.get("origin"),
                    "destination": t.get("destination"),
                    "status": t.get("status"),
                    "completed_at": t.get("completed_at"),
                    "settled_at": t.get("settled_at"),
                    "advance_amount": res.advance_amount,
                    "total_road_expenses": res.total_road_expenses,
                    "driver_batta": res.driver_batta,
                    "net_balance": res.net_balance,
                    "status_label_en": res.status_label_en,
                }
            )
        total_batta = round(sum(r["driver_batta"] for r in rows), 2)
        total_payable = round(
            sum(-r["net_balance"] for r in rows if r["net_balance"] < 0), 2
        )
        total_refund = round(
            sum(r["net_balance"] for r in rows if r["net_balance"] > 0), 2
        )

    return _ok(
        {
            "profile": {k: _jsonable(v) for k, v in profile.items()},
            "trips": rows,
            "totals": {
                "total_batta": total_batta,
                "total_payable": total_payable,
                "total_refund": total_refund,
            },
        }
    )