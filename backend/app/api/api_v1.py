"""Phase 0 JSON API — transport-agnostic endpoints for the React SPA + mobile.

Guardrails (per the architecture review):
  1. Real HTTP status codes (401/403) with JSON error payloads — never the
     browser 303 redirect, which fetch()/axios cannot consume cleanly.
  2. Auth via `Authorization: Bearer <token>` OR the session cookie (both resolve
     through the same in-memory session store in core.security).
  3. No single-use CSRF token consumption on these JSON mutations — React can
     fire parallel requests without racing on a consumed token. CSRF for
     /api/v1 is mitigated by Bearer-token-in-header + a non-GET, non-form
     JSON content-type requirement.

Frontend (regardless of framework) and the Phase-2 mobile app both speak to this
router. It reuses the existing `db/queries/*` helpers, so there is zero business
logic duplication — only thin HTTP adaptation.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from backend.app.core.config import settings
from backend.app.core.password import hash_password, verify_password
from backend.app.core.security import (
    AUTH_COOKIE,
    clear_login_failures,
    create_session,
    destroy_session,
    login_allowed,
    register_login_failure,
)
from backend.app.core.security import get_current_user, require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.dashboards import (
    active_trip_progress,
    admin_kpis,
    approved_cash_net,
    driver_today_logged,
    manager_kpis,
    open_escalations,
    open_escalations_detail,
)
from backend.app.db.queries.expenses import action_expense_status, get_expenses_for_trip, insert_expense
from backend.app.db.queries.fleets import (
    count_active_vehicles,
    deactivate_fleet,
    fleet_phone_exists,
    get_all_fleets,
    get_all_plans,
    get_default_fleet,
    get_fleet_by_id,
    get_fleet_email_context,
    get_fleet_entitlement,
    insert_fleet,
    is_trial_active,
    reactivate_fleet,
    update_fleet,
)
from backend.app.db.queries.settlement import get_settled_trips
from backend.app.db.queries.trips import (
    active_trip_exists,
    get_active_trip_for_driver,
    get_trip_by_code,
    get_trip_stats_by_code,
    get_trips_for_user,
    insert_trip,
    pending_expense_count,
    settle_trip as mark_trip_settled,
    trip_status,
)
from backend.app.db.queries.users import (
    create_user,
    deactivate_user,
    get_all_users,
    get_driver_batta_profile,
    get_user_by_id,
    get_user_fleet_id,
    reactivate_user,
    update_user,
)
from backend.app.db.queries.billing import (
    mark_webhook_processed,
    webhook_already_processed,
)
from backend.app.db.queries.vehicles import (
    deactivate_vehicle,
    get_all_vehicles,
    insert_vehicle,
    reactivate_vehicle,
    update_vehicle,
    vehicle_number_exists,
)
from backend.app.db.queries.benchmarks import (
    delete_benchmark,
    get_all_benchmarks,
    insert_benchmark,
    update_benchmark,
)
from backend.app.services.audit.cash import compute_settlement, resolve_trip_batta
from backend.app.services.email.client import (
    manager_onboarding_email_context,
    send_manager_onboarding_email_sync,
)
from backend.app.services.pdf.settlement import build_settlement_pdf
from backend.app.services.rules.constants import GOODS_TYPES
from backend.app.services.rules.evaluate import RuleInput, evaluate_expense

router = APIRouter(prefix="/api/v1")

from backend.app.schemas.api_v1 import (  # noqa: E402  (response models)
    AuthMe,
    BillingOverview,
    BillingSubscribeResult,
    BillingVehicleSlotResult,
    ChangePasswordResult,
    CreateTripResult,
    DashboardOverview,
    Data,
    DriverSalary,
    EscalationRow,
    ExpenseAccepted,
    ExpenseActionResult,
    FleetBilling,
    LoginResult,
    LogoutResult,
    Plan,
    ResourceAck,
    RulesData,
    SettleTripResult,
    ToggleAck,
    TripDetailData,
    TripListItem,
)

JSON_EXPENSE_TYPES: tuple[str, ...] = (
    "FUEL", "DEF", "TOLL", "REPAIR", "CHALLAN", "MISC", "GOODS_BUY", "GOODS_SALE",
)

PLATE_RE = re.compile(settings.plate_regex)
from backend.app.db.queries.users import get_user_by_username
from backend.app.db.queries.fleets import (
    bump_vehicle_limit,
    set_plan_subscription,
    set_yearly_subscription,
    start_trial_subscription,
)
from backend.app.services.billing.razorpay import (
    MONTHLY_PRICE,
    YEARLY_PRICE,
    VEHICLE_SLOT_PRICE,
    create_payment_link,
)


# ---------------------------------------------------------------------------#
# Serialization helpers
# ---------------------------------------------------------------------------#
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
    """Return a `{ "data": <payload> }` envelope for a success response.

    Returns a plain dict (not a JSONResponse) so FastAPI's `response_model` is
    applied — every endpoint is decorated with a typed Pydantic response model.
    """
    return {"data": _jsonable(payload)}


def _created(payload: Any) -> dict:
    """Return a `{ "data": <payload> }` envelope for a 201 Created response."""
    return {"data": _jsonable(payload)}


def _bad(msg: str, code: str = "BAD_REQUEST") -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": msg, "code": code})


def _not_found(msg: str = "not found") -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": msg, "code": "NOT_FOUND"})


def _identity(request: Request) -> dict:
    return get_current_user(request) or {}
# ---------------------------------------------------------------------------#
# Dashboard overview — one endpoint, role-aware
# ---------------------------------------------------------------------------#
@router.get("/dashboard/overview", response_model=Data[DashboardOverview])
def api_dashboard_overview(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    role = user.get("role", "")
    user_id = user.get("user_id")

    with get_db() as conn:
        if role == "super_admin":
            data = {"role": role, "kpis": admin_kpis(conn)}
        elif role == "trip_manager":
            data = {
                "role": role,
                "kpis": manager_kpis(conn, manager_id=user_id),
                "active_trips": active_trip_progress(conn, manager_id=user_id),
                "escalations": open_escalations(conn, limit=20, manager_id=user_id),
            }
        elif role == "driver":
            trip = get_active_trip_for_driver(conn, user_id)
            trip_code = trip["trip_code"] if trip else None
            data = {
                "role": role,
                "trip": _jsonable(trip),
                "today_logged": driver_today_logged(conn, trip_code) if trip_code else 0.0,
                "cash_in_hand": (trip["advance_amount"] or 0.0) + approved_cash_net(conn, trip_code)
                - float(trip.get("driver_batta_amount") or 2500.00)
                if trip_code else 0.0,
            }
        else:
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )

    return _ok(data)


# ---------------------------------------------------------------------------#
# Trips
# ---------------------------------------------------------------------------#
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
        role = user.get("role", "")
        if role == "trip_manager" and trip["created_by"] != user.get("user_id"):
            return JSONResponse(status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"})
        if role == "driver" and trip["driver_user_id"] != user.get("user_id"):
            return JSONResponse(status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"})
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
# ---------------------------------------------------------------------------#
# WhatsApp escalation feed (JSON) — manager & super_admin quick-reply actions
# ---------------------------------------------------------------------------#
@router.get("/whatsapp/escalations", response_model=Data[list[EscalationRow]])
def api_whatsapp_escalations(request: Request):
    """Flagged / pending expenses as a chat-thread feed for manager quick-reply.

    Manager sees only the expenses on trips they created; super_admin sees all.
    Each item carries trip driver + vehicle so the escalation UI can label who
    logged the anomaly.
    """
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    manager_id = (
        user.get("user_id") if user.get("role") == "trip_manager" else None
    )
    with get_db() as conn:
        rows = open_escalations_detail(conn, limit=50, manager_id=manager_id)
    return _ok(rows)
# ---------------------------------------------------------------------------#
# Expenses — mutations (JSON body, no single-use CSRF)
# ---------------------------------------------------------------------------#
@router.post("/expenses", response_model=Data[ExpenseAccepted])
async def api_create_expense(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - malformed body
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")

    trip_code = str(body.get("trip_code", "")).strip().upper()
    exp_type = str(body.get("exp_type", "")).upper()
    amount = float(body.get("amount", 0.0))
    odometer = float(body.get("odometer") or 0.0)
    liters = float(body.get("liters") or 0.0)
    rate = float(body.get("rate") or 0.0)

    if exp_type not in JSON_EXPENSE_TYPES:
        return _bad("invalid expense type", "INVALID_EXPENSE_TYPE")

    with get_db() as conn:
        if trip_status(conn, trip_code) != "ACTIVE":
            return _not_found("trip not active")
        verdict = evaluate_expense(
            RuleInput(exp_type=exp_type, amount=amount, liters=liters, rate=rate, odometer=odometer)
        )
        manager_status = "PENDING" if verdict.flagged or exp_type in GOODS_TYPES else "APPROVED"
        insert_expense(
            conn,
            trip_code=trip_code,
            exp_type=exp_type,
            amount=amount,
            liters=liters,
            rate=rate,
            odometer=odometer,
            is_flagged=bool(verdict.flagged),
            flag_reason=verdict.reason or None,
            manager_status=manager_status,
        )
        if odometer > 0:
            cur = conn.cursor()
            cur.execute(
                "UPDATE trips SET current_odo = GREATEST(current_odo, %s) WHERE trip_code = %s",
                (odometer, trip_code),
            )
    return _created(
        {
            "accepted": True,
            "trip_code": trip_code,
            "exp_type": exp_type,
            "manager_status": manager_status,
            "is_flagged": bool(verdict.flagged),
            "flag_reason": verdict.reason or None,
        }
    )


@router.post("/expenses/{expense_id}/action", response_model=Data[ExpenseActionResult])
async def api_action_expense(request: Request, expense_id: int):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    action = str((body or {}).get("action", "")).upper()
    if action not in ("APPROVE", "REJECT"):
        return _bad("action must be APPROVE or REJECT", "INVALID_ACTION")
    status = "APPROVED" if action == "APPROVE" else "REJECTED"

    with get_db() as conn:
        trip_code = action_expense_status(conn, expense_id, status)
    if not trip_code:
        return _not_found("expense not found")
    return _ok({"expense_id": expense_id, "status": status, "trip_code": trip_code})


# ---------------------------------------------------------------------------#
# Trip start & settle (JSON mutations, feature-complete contract)
# ---------------------------------------------------------------------------#
def _resolve_trip_fleet(conn, user: dict) -> int | None:
    """Resolve the tenant fleet for a new trip (mirrors trips.py logic)."""
    fleet_id = get_user_fleet_id(conn, user.get("user_id")) if user.get("user_id") else None
    if fleet_id is None:
        default = get_default_fleet(conn)
        if default:
            fleet_id = default["id"]
    return fleet_id


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
        return _bad("advance_amount and start_odo must be non-negative", "INVALID_NUMBER")
    if not PLATE_RE.match(vehicle_no):
        return _bad("invalid license plate", "INVALID_PLATE")
    digits = re.sub(r"\D", "", driver_phone or "")
    if not (digits.startswith("91") and len(digits) == 12):
        return _bad("driver_phone must be a valid +91 number", "INVALID_PHONE")

    with get_db() as conn:
        fleet_id = _resolve_trip_fleet(conn, user)
        if fleet_id is None:
            return _bad("no fleet configured for this user", "NO_FLEET")
        if active_trip_exists(conn, fleet_id=fleet_id):
            return JSONResponse(
                status_code=409,
                content={"error": "an active trip already exists for this fleet", "code": "ACTIVE_TRIP_EXISTS"},
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
        if user.get("role") == "trip_manager" and trip.get("created_by") != user.get("user_id"):
            return JSONResponse(status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"})
        if pending_expense_count(conn, trip_code):
            return JSONResponse(
                status_code=409,
                content={"error": "cannot settle: pending expenses remain", "code": "PENDING_EXPENSES"},
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


@router.get("/settlements/{trip_code}/pdf", response_class=Response, response_model=None)
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
        if user.get("role") == "trip_manager" and trip.get("created_by") != user.get("user_id"):
            return Response("Forbidden", status_code=403)
        if user.get("role") == "driver" and trip.get("driver_user_id") != user.get("user_id"):
            return Response("Forbidden", status_code=403)
        expenses = get_expenses_for_trip(conn, trip_code)

    pdf_bytes = build_settlement_pdf(trip, expenses)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={trip_code}_Settlement.pdf"},
    )
@router.get("/driver/salary", response_model=Data[DriverSalary])
def api_driver_salary(request: Request):
    """Read-only salary/batta summary for the logged-in driver.

    Returns the driver's batta profile plus a per-trip settlement breakdown
    (batta resolved, net payable/refund) for every trip assigned to them.
    Data is strictly read-only and scoped to the caller's own trips.
    """
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
            rows.append({
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
            })
        total_batta = round(sum(r["driver_batta"] for r in rows), 2)
        total_payable = round(sum(
            -r["net_balance"] for r in rows if r["net_balance"] < 0
        ), 2)
        total_refund = round(sum(
            r["net_balance"] for r in rows if r["net_balance"] > 0
        ), 2)

    return _ok({
        "profile": {k: _jsonable(v) for k, v in profile.items()},
        "trips": rows,
        "totals": {
            "total_batta": total_batta,
            "total_payable": total_payable,
            "total_refund": total_refund,
        },
    })
# ---------------------------------------------------------------------------#
# ---------------------------------------------------------------------------#
# Fuel benchmarks CRUD (JSON)
# ---------------------------------------------------------------------------#
@router.get("/benchmarks", response_model=Data[list[dict[str, Any]]])
def api_get_benchmarks(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    with get_db() as conn:
        benchmarks = get_all_benchmarks(conn)
    return _ok(benchmarks)


@router.post("/benchmarks", response_model=Data[ResourceAck])
async def api_create_benchmark(request: Request):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    state_code = str(body.get("state_code", "")).strip().upper()
    state_name = str(body.get("state_name", "")).strip()
    if not state_code or not state_name:
        return _bad("state_code and state_name are required", "MISSING_FIELDS")
    price = float(body.get("benchmark_price_per_liter", 0.0))
    tolerance = float(body.get("tolerance_pct", 8.0))
    effective_date = body.get("effective_date") or None
    with get_db() as conn:
        new_id = insert_benchmark(conn, state_code, state_name, price, tolerance, effective_date)
    return _created({"id": new_id})


@router.put("/benchmarks/{bid}", response_model=Data[ResourceAck])
async def api_update_benchmark(request: Request, bid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    state_code = str(body.get("state_code", "")).strip().upper()
    state_name = str(body.get("state_name", "")).strip()
    if not state_code or not state_name:
        return _bad("state_code and state_name are required", "MISSING_FIELDS")
    price = float(body.get("benchmark_price_per_liter", 0.0))
    tolerance = float(body.get("tolerance_pct", 8.0))
    effective_date = body.get("effective_date") or None
    with get_db() as conn:
        ok = update_benchmark(conn, bid, state_code, state_name, price, tolerance, effective_date)
    if not ok:
        return _not_found("benchmark not found")
    return _ok({"id": bid})


@router.delete("/benchmarks/{bid}", status_code=204, response_model=None)
def api_delete_benchmark(request: Request, bid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        ok = delete_benchmark(conn, bid)
    if not ok:
        return _not_found("benchmark not found")
    return JSONResponse(status_code=204, content=None)
# ---------------------------------------------------------------------------#
# Fleet CRUD (JSON) — Super Admin
# ---------------------------------------------------------------------------#
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
            return JSONResponse(status_code=409, content={"error": "fleet with this phone exists", "code": "DUP_PHONE"})
        new_id = insert_fleet(conn, owner_name, phone, email.strip() if email else None, plan)
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
            return JSONResponse(status_code=409, content={"error": "fleet with this phone exists", "code": "DUP_PHONE"})
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
# ---------------------------------------------------------------------------#
# Vehicles CRUD (JSON) — trip_manager / super_admin
# ---------------------------------------------------------------------------#
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


def _resolve_vehicle_fleet(conn, user: dict) -> int | None:
    """Resolve the fleet a new vehicle belongs to (mirrors vehicles.py flow)."""
    fleet_id = get_user_fleet_id(conn, user.get("user_id")) if user.get("user_id") else None
    if fleet_id is None:
        default = get_default_fleet(conn)
        if default:
            fleet_id = default["id"]
    return fleet_id


def _vehicle_limit_ok(conn, fleet_id: int) -> bool:
    """True when the fleet subscription allows registering one more vehicle."""
    entitlement = get_fleet_entitlement(conn, fleet_id)
    if not entitlement:
        return False
    active = entitlement["subscription_status"] == "ACTIVE" or is_trial_active(conn, fleet_id)
    if not active:
        return False
    return count_active_vehicles(conn, fleet_id) < entitlement["vehicle_limit"]


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
    if not PLATE_RE.match(number):
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
        if not _vehicle_limit_ok(conn, fleet_id):
            return JSONResponse(
                status_code=402,
                content={"error": "vehicle limit reached for this fleet", "code": "VEHICLE_LIMIT"},
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
    user = _identity(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    number = str(body.get("vehicle_number", "")).strip().upper()
    if not PLATE_RE.match(number):
        return _bad("invalid license plate", "INVALID_PLATE")
    make_model = (body.get("make_model") or "").strip() or None
    tank_capacity_liters = float(body.get("tank_capacity_liters", 350.0))
    expected_km_per_liter = float(body.get("expected_km_per_liter", 4.0))
    owner_phone = (body.get("owner_phone") or "").strip() or None

    with get_db() as conn:
        if vehicle_number_exists(conn, number, exclude_id=vid):
            return _bad("vehicle number already exists", "DUP_VEHICLE")
        ok = update_vehicle(
            conn, vid, number, make_model, tank_capacity_liters, expected_km_per_liter, owner_phone
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


@router.get("/users", response_model=Data[list[dict[str, Any]]])
def api_users(request: Request):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        users = get_all_users(conn)
    # Never leak password hashes to the client.
    for u in users:
        u.pop("password_hash", None)
    return _ok(users)


# ---------------------------------------------------------------------------#
# Users CRUD (JSON) — Super Admin
# ---------------------------------------------------------------------------#
VALID_ROLES: tuple[str, ...] = ("super_admin", "trip_manager", "driver")


def _resolve_user_fleet(conn) -> dict | None:
    """Resolve the fleet a freshly-created trip manager belongs to.

    The manager's own `users.fleet_id` is NULL at creation (create_user does not
    bind one), so fall back to the default active fleet — the same resolution
    the trip/vehicle creation paths use.
    """
    default = get_default_fleet(conn)
    if default is None:
        return None
    return get_fleet_email_context(conn, default["id"])


def _login_url(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/login"


def _manager_onboarding_payload(
    conn, new_id: int, username: str, temporary_password: str, manager_email: str | None,
    request: Request,
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
    full_name = (user or {}).get("full_name") or username
    ctx = manager_onboarding_email_context(
        manager_full_name=full_name,
        manager_username=username,
        temporary_password=temporary_password,
        fleet=fleet,
        login_url=_login_url(request),
    )
    ctx["to_email"] = manager_email
    return ctx


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
    username = str(body.get("username", "")).strip()
    full_name = str(body.get("full_name", "")).strip()
    role = str(body.get("role", ""))
    password = str(body.get("password", ""))
    if role not in VALID_ROLES or not password:
        return _bad("invalid role or missing password", "VALIDATION")
    phone = (body.get("phone") or "").strip() or None
    email = (body.get("email") or "").strip() or None
    batta_type = (body.get("batta_type") or "").strip() or None
    default_batta_rate = body.get("default_batta_rate")
    if role != "driver":
        batta_type = None
        default_batta_rate = None
    with get_db() as conn:
        new_id = create_user(
            conn, username, hash_password(password), full_name, role,
            phone, email, created_by=user.get("user_id"),
            batta_type=batta_type,
            default_batta_rate=default_batta_rate,
        )
        if role == "trip_manager":
            ctx = _manager_onboarding_payload(
                conn, new_id, username, password, email, request
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
    return _ok({"id": uid, "is_active": should_activate})


# ---------------------------------------------------------------------------#
# Change Password (JSON) — logged-in user, any role
# ---------------------------------------------------------------------------#
@router.post("/auth/change-password", response_model=Data[ChangePasswordResult])
async def api_change_password(request: Request):
    """Verify the current password and set a new one for the logged-in user.

    Transport-agnostic JSON mirror of the HTML `POST /users/change-password`
    flow. Bearer-token (or cookie) auth; no single-use CSRF consumed so React
    form submits behave like any other `/api/v1` mutation.
    """
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    if not user:
        return _bad("not authenticated", "UNAUTHENTICATED")

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
        return _bad("new password and confirm password do not match", "PASSWORD_MISMATCH")

    with get_db() as conn:
        db_user = get_user_by_id(conn, user.get("user_id"))
    if not db_user:
        return _not_found("user not found")
    if not verify_password(current_password, db_user["password_hash"]):
        return _bad("current password is incorrect", "WRONG_PASSWORD")

    new_hash = hash_password(new_password)
    with get_db() as conn:
        update_user(
            conn, user["user_id"], db_user["full_name"], db_user["role"],
            db_user["phone"], db_user["email"], password_hash=new_hash,
        )
    return _ok({"id": user["user_id"], "password_changed": True})


# ---------------------------------------------------------------------------#
# Drivers (JSON) — list driver users for Trip Manager / Super Admin
# ---------------------------------------------------------------------------#
@router.get("/drivers", response_model=Data[list[dict[str, Any]]])
def api_drivers(request: Request):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        drivers = get_all_users(conn, role_filter="driver")
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
    username = str(body.get("username", "")).strip()
    full_name = str(body.get("full_name", "")).strip()
    password = str(body.get("password", ""))
    if not username or not full_name or not password:
        return _bad("username, full_name and password are required", "MISSING_FIELDS")
    phone = (body.get("phone") or "").strip() or None
    email = (body.get("email") or "").strip() or None
    batta_type = (body.get("batta_type") or "").strip() or None
    default_batta_rate = body.get("default_batta_rate")
    with get_db() as conn:
        new_id = create_user(
            conn, username, hash_password(password), full_name, "driver",
            phone, email, created_by=user.get("user_id"),
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
    with get_db() as conn:
        existing = get_user_by_id(conn, uid)
        if existing is None or existing.get("role") != "driver":
            return _not_found("driver not found")
        ok = update_user(
            conn, uid, full_name, "driver", phone, email, password_hash=pw_hash,
            batta_type=batta_type, default_batta_rate=default_batta_rate,
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
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    should_activate = bool((body or {}).get("activate", False))
    with get_db() as conn:
        existing = get_user_by_id(conn, uid)
        if existing is None or existing.get("role") != "driver":
            return _not_found("driver not found")
        if should_activate:
            reactivate_user(conn, uid)
        else:
            deactivate_user(conn, uid)
    return _ok({"id": uid, "is_active": should_activate})
# ---------------------------------------------------------------------------#
# Auth (JSON) — login / me / logout
# ---------------------------------------------------------------------------#
# These moved here from `api/auth.py`; the HTML login/logout pages were removed
# from the backend and the React SPA (`frontend/`) is the only UI. The legacy
# `auth` router is no longer mounted by `main.py`.


def _client_ip(request: Request) -> str:
    forwarded = getattr(request, "headers", {}).get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if getattr(request, "client", None):
        return request.client.host
    return "unknown"


@router.post("/auth/login", response_model=LoginResult)
async def api_auth_login(request: Request, response: Response):
    """Authenticate and return a Bearer token + user as JSON.

    Accepts an `application/json` body OR a form-encoded body so both the SPA
    (JSON) and legacy/mobile clients keep working. Always returns JSON.
    """
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
            content={"error": "locked", "code": "LOCKED", "retry_after_seconds": lock_remaining},
        )
    with get_db() as conn:
        user = get_user_by_username(conn, username)
    if user is None or not verify_password(password, user["password_hash"]):
        remaining = register_login_failure(ip)
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_credentials", "code": "INVALID_CREDENTIALS", "attempts_remaining": remaining},
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
# --------------------------------------------------------------------------- #
# Billing (JSON) — plan upgrade / vehicle-slot purchases
# --------------------------------------------------------------------------- #
def _billing_fleet(conn, user_id: int):
    fid = get_user_fleet_id(conn, user_id)
    if not fid:
        default = get_default_fleet(conn)
        fid = default["id"] if default else None
    if not fid:
        return None
    return get_fleet_by_id(conn, fid)


@router.get("/billing/overview", response_model=Data[BillingOverview])
def api_billing_overview(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        fleet = _billing_fleet(conn, user.get("user_id"))
        ent = get_fleet_entitlement(conn, fleet["id"]) if fleet else None
    plans = [
        {
            "code": "TRIAL", "name": "Trial Pack", "price": 0,
            "period": "15 days", "vehicle_limit": 1,
            "description": "15 days for free, 1 vehicle",
        },
        {
            "code": "MONTHLY", "name": "Monthly",
            "price": int(MONTHLY_PRICE), "period": "month",
            "vehicle_limit": 1, "description": "1 vehicle \u00b7 monthly",
        },
        {
            "code": "YEARLY", "name": "Yearly",
            "price": int(YEARLY_PRICE), "period": "year",
            "vehicle_limit": 1, "description": "1 vehicle \u00b7 yearly (25% off)",
        },
    ]
    return _ok({
        "fleet": {
            "name": (fleet or {}).get("owner_name", "Your Fleet"),
            "id": (fleet or {}).get("id"),
            "subscription_status": (ent or {}).get("subscription_status", "?"),
            "vehicle_count": (ent or {}).get("vehicle_count", 0),
            "vehicle_limit": (ent or {}).get("vehicle_limit", 1),
            "vehicle_slot_price": int(VEHICLE_SLOT_PRICE),
        },
        "plans": plans,
    })


async def _read_json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    return body if isinstance(body, dict) else {}


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
@router.post("/billing/subscribe", response_model=Data[BillingSubscribeResult])
async def api_billing_subscribe(request: Request):
    """Subscribe to a plan; returns a JSON `redirect_url` to Razorpay."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    body = await _read_json_body(request)
    plan_code = str(body.get("plan_code", "")).upper()

    with get_db() as conn:
        fleet = _billing_fleet(conn, user.get("user_id"))
        if fleet is None:
            return _bad("no fleet associated with this account")
        if plan_code == "TRIAL":
            start_trial_subscription(conn, fleet["id"])
            return _ok({"redirect_url": "/fleets", "activated": True, "trial": True})
        if plan_code not in ("MONTHLY", "YEARLY"):
            return _bad("unknown plan_code", "INVALID_PLAN")
        cust = {
            "name": fleet.get("owner_name", ""),
            "contact": fleet.get("phone", ""),
            "email": fleet.get("email", ""),
        }
        if plan_code == "MONTHLY":
            ref, price, desc = f"fleet_{fleet['id']}_monthly", MONTHLY_PRICE, "VK Monthly Plan"
        else:
            ref, price, desc = f"fleet_{fleet['id']}_yearly", YEARLY_PRICE, "VK Yearly Plan"
    try:
        link = create_payment_link(price, cust, desc, reference_id=ref)
    except Exception as exc:  # noqa: BLE001
        return _bad(f"payment link failed: {exc}", "PAYMENT_LINK_FAILED")
    url = link.get("short_url") or link.get("long_url")
    return _ok({"redirect_url": url, "payment_link": link})


@router.post("/billing/vehicle-slot", response_model=Data[BillingVehicleSlotResult])
async def api_billing_vehicle_slot(request: Request):
    """Purchase an extra vehicle slot; returns JSON `redirect_url`."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    with get_db() as conn:
        fleet = _billing_fleet(conn, user.get("user_id"))
        if fleet is None:
            return _bad("no fleet associated with this account")
        cust = {
            "name": fleet.get("owner_name", ""),
            "contact": fleet.get("phone", ""),
            "email": fleet.get("email", ""),
        }
    try:
        link = create_payment_link(
            VEHICLE_SLOT_PRICE,
            cust,
            "VK Extra Vehicle Slot",
            reference_id=f"fleet_{fleet['id']}_vehicle_slot",
        )
    except Exception as exc:  # noqa: BLE001
        return _bad(f"payment link failed: {exc}", "PAYMENT_LINK_FAILED")
    url = link.get("short_url") or link.get("long_url")
    return _ok({"redirect_url": url, "payment_link": link})
# --------------------------------------------------------------------------- #
# Rules engine (JSON) — read-only anomaly-rule explainer data
# --------------------------------------------------------------------------- #
@router.get("/rules", response_model=Data[RulesData])
def api_rules(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    rules = {
        "FUEL": [
            "Math integrity: flags if Amount differs from Liters x Rate by more than Rs 10.",
            f"Price benchmark: rate must be inside base Rs {settings.benchmark_price}/L band.",
            f"Tank capacity: claimed liters can not exceed {settings.tank_capacity_liters:.0f}L.",
            "Odometer rollback: flags if new reading is lower than the previous fuel reading.",
            f"Mileage check: km/L below {settings.expected_kml:.1f} x 70% is flagged.",
        ],
        "TOLL": [
            "Always flagged", "Cash toll claims disallowed on FASTag corridors.",
        ],
        "REPAIR": [
            "Any repair claim above Rs 3,000 requires owner pre-approval.",
        ],
        "CHALLAN": [
            "Always flagged; verified against the e-challan portal.",
        ],
        "DEF": [
            f"Price benchmark: rate above Rs {settings.def_rate_max:.0f}/l ceiling is flagged.",
            f"Consumption ratio: DEF outside {settings.def_min_ratio_pct:.0f}%-{settings.def_max_ratio_pct:.0f}% of diesel is flagged.",
        ],
    }
    return _ok(rules)