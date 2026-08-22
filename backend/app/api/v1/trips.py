from __future__ import annotations

import re as _re
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from backend.app.api.v1.deps import (
    _bad,
    _created,
    _identity,
    _jsonable,
    _not_found,
    _ok,
    _trip_forbidden,
)
from backend.app.core.config import settings
from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.expenses import (
    get_expenses_for_trip,
    get_ledger_expenses_for_trip,
    insert_expense,
)
from backend.app.db.queries.fleets import get_default_fleet
from backend.app.db.queries.settlement import get_settled_trips
from backend.app.db.queries.trips import (
    active_trip_exists,
    get_trip_by_code,
    get_trip_stats_by_code,
    get_trips_for_user,
    insert_trip,
    pending_expense_count,
)
from backend.app.db.queries.trips import (
    settle_trip as mark_trip_settled,
)
from backend.app.db.queries.users import (
    get_driver_batta_profile,
    get_user_by_id,
    get_user_fleet_id,
)
from backend.app.schemas.api_v1 import (
    CreateTripResult,
    Data,
    DriverSalary,
    SettleTripResult,
    TripDetailData,
    TripListItem,
)
from backend.app.services.audit.cash import compute_settlement, resolve_trip_batta
from backend.app.services.pdf.settlement import build_settlement_pdf
from backend.app.services.state import state_code_from_plate

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
        # Compute settlement from the FULL ledger (provisions are part of the
        # arithmetic), but expose only the real driver expenses in the payload.
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
        ledger_expenses = get_ledger_expenses_for_trip(conn, trip_code)

    return _ok({
        "trip": trip,
        "expenses": ledger_expenses,
    })
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
    advance_amount = float(body.get("advance_amount", 0.0))
    start_odo = float(body.get("start_odo", 0.0))
    vehicle_id = body.get("vehicle_id") or None
    driver_user_id = body.get("driver_user_id") or None

    if not vehicle_no:
        return _bad("vehicle_no is required", "MISSING_FIELDS")
    if advance_amount <= 0:
        return _bad("advance_amount must be greater than zero", "INVALID_ADVANCE")
    if start_odo < 0:
        return _bad("start_odo must be non-negative", "INVALID_NUMBER")
    if not _PLATE_RE.match(vehicle_no):
        return _bad("invalid license plate", "INVALID_PLATE")

    # The operating state is derived from the vehicle plate's 2-letter RTO
    # prefix (e.g. UP32TA1234 -> UP). It drives the per-state fuel benchmark
    # band the rules engine uses for this trip's fuel expenses.
    state_code = state_code_from_plate(vehicle_no)

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
        # Driver name, phone, and batta are all resolved from the users table
        # via driver_user_id — the client sends only the ID.
        # Ownership: a manager may only dispatch drivers they created; a
        # foreign driver id must never be usable cross-manager (403).
        driver_row = get_user_by_id(conn, driver_user_id) if driver_user_id else None
        if driver_row is None or driver_row.get("role") != "driver":
            return _bad("unknown driver selected", "UNKNOWN_DRIVER")
        if (
            user.get("role", "super_admin") != "super_admin"
            and driver_row.get("created_by") != user.get("user_id")
        ):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        driver = get_driver_batta_profile(conn, driver_user_id)
        if not driver:
            return _bad("unknown driver selected", "UNKNOWN_DRIVER")
        driver_batta_amount = resolve_trip_batta(driver)
        if driver_batta_amount <= 0:
            return _bad(
                "selected driver has no batta configured; batta must be greater than zero",
                "INVALID_BATTA",
            )
        trip_code = insert_trip(
            conn,
            fleet_id,
            vehicle_no,
            start_odo,
            created_by=user.get("user_id"),
            driver_user_id=driver_user_id,
            vehicle_id=vehicle_id,
            state_code=state_code,
        )
        # Auto-post the two unified-ledger legs for this trip: Cash Advance (credit
        # to driver) and Driver Salary/batta (debit). They are fixed provisions, so
        # they are inserted APPROVED and bypass the rules engine (no flag). The
        # settlement engine (`compute_settlement`) now reads these two amounts from
        # the ledger instead of from the trip columns alone, so advance/batta appear
        # in one place — the expenses ledger — for managers and the driver.
        if advance_amount > 0:
            insert_expense(
                conn, trip_code=trip_code, exp_type="CASH_ADVANCE",
                amount=advance_amount, liters=0.0, rate=0.0, odometer=0.0,
                is_flagged=False, flag_reason=None, manager_status="APPROVED",
            )
        if driver_batta_amount > 0:
            insert_expense(
                conn, trip_code=trip_code, exp_type="DRIVER_SALARY",
                amount=driver_batta_amount, liters=0.0, rate=0.0, odometer=0.0,
                is_flagged=False, flag_reason=None, manager_status="APPROVED",
            )
    return _created({"trip_code": trip_code, "status": "ACTIVE"})
@router.post("/trips/{trip_code}/settle", response_model=Data[SettleTripResult])
async def api_settle_trip(request: Request, trip_code: str):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    trip_code = trip_code.strip().upper()

    # Parse the closing odometer from the request body.
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}

    end_odo = body.get("end_odo")
    if end_odo is not None:
        try:
            end_odo = float(end_odo)
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=400,
                content={"error": "end_odo must be a number", "code": "INVALID_ODO"},
            )

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

        # ---- Check 4: end_odo >= start_odo ---------------------------------
        start_odo = float(trip.get("start_odo") or 0.0)
        if end_odo is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "closing odometer reading (end_odo) is required to settle",
                    "code": "MISSING_END_ODO",
                },
            )
        if end_odo < start_odo:
            return JSONResponse(
                status_code=400,
                content={
                    "error": (
                        f"Closing odometer ({end_odo}) is lower than start odometer "
                        f"({start_odo}). Please correct and retry."
                    ),
                    "code": "INVALID_END_ODO",
                },
            )

        # ---- Check 5: Fuel efficiency within 1.5-12 km/L band ---------------
        expenses = get_expenses_for_trip(conn, trip_code)
        settlement = compute_settlement(trip, expenses)
        if settlement.avg_kml is not None:
            if settlement.avg_kml < 1.5:
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": (
                            f"Fuel efficiency is {settlement.avg_kml} km/L — below the "
                            f"minimum of 1.5 km/L for commercial vehicles. "
                            f"Verify fuel litres and odometer readings."
                        ),
                        "code": "FUEL_EFFICIENCY_LOW",
                    },
                )
            if settlement.avg_kml > 12.0:
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": (
                            f"Fuel efficiency is {settlement.avg_kml} km/L — exceeds the "
                            f"maximum of 12 km/L for commercial vehicles. "
                            f"Verify fuel litres and odometer readings."
                        ),
                        "code": "FUEL_EFFICIENCY_HIGH",
                    },
                )

        mark_trip_settled(conn, trip_code, manager_id=user.get("user_id"), end_odo=end_odo)
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
        # Resolve consent actor names (Option 1): resolve the user rows for the
        # stored manager_consent_by / driver_consent_by ids so the PDF footer can
        # print human-readable acceptance names. None/null-consent trips print
        # the consent lines as dash (no actor recorded yet).
        manager_name = None
        driver_consent_name = None
        if trip.get("manager_consent_by"):
            m = get_user_by_id(conn, trip["manager_consent_by"])
            manager_name = m.get("full_name") if m else None
        if trip.get("driver_consent_by"):
            d = get_user_by_id(conn, trip["driver_consent_by"])
            driver_consent_name = d.get("full_name") if d else None

    pdf_bytes = build_settlement_pdf(
        trip, expenses,
        manager_consent_name=manager_name,
        driver_consent_name=driver_consent_name,
    )
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
