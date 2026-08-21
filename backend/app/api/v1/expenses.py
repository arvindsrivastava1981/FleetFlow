from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.dashboards import open_escalations_detail
from backend.app.db.queries.expenses import (
    action_expense_status,
    get_expense_trip_code,
    insert_expense,
)
from backend.app.db.queries.benchmarks import get_benchmark_price_and_tolerance
from backend.app.db.queries.trips import get_trip_by_code, trip_status, update_trip_odometer
from backend.app.services.rules.bands import DEFAULT_BAND, derive_band
from backend.app.services.rules.constants import GOODS_TYPES
from backend.app.services.rules.evaluate import RuleInput, evaluate_expense

from backend.app.api.v1.deps import _bad, _created, _identity, _not_found, _ok, _trip_forbidden
from backend.app.schemas.api_v1 import (
    Data,
    EscalationRow,
    ExpenseAccepted,
    ExpenseActionResult,
)

router = APIRouter(prefix="/api/v1")

JSON_EXPENSE_TYPES: tuple[str, ...] = (
    "FUEL", "DEF", "TOLL", "REPAIR", "CHALLAN", "MISC", "GOODS_BUY", "GOODS_SALE",
    "CASH_ADVANCE", "DRIVER_SALARY",
)

# Auto-posted at trip-creation (never submitted via the rule/flag pipeline).
# CASH_ADVANCE credits the driver (money given), DRIVER_SALARY debits the trip
# (batta earned). Both are always APPROVED and never flagged.
AUTO_LEDGER_TYPES: frozenset[str] = frozenset({"CASH_ADVANCE", "DRIVER_SALARY"})


@router.get("/whatsapp/escalations", response_model=Data[list[EscalationRow]])
def api_whatsapp_escalations(request: Request):
    """Flagged / pending expenses as a chat-thread feed for manager quick-reply."""
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    manager_id = user.get("user_id") if user.get("role") == "trip_manager" else None
    with get_db() as conn:
        rows = open_escalations_detail(conn, limit=50, manager_id=manager_id)
    return _ok(rows)


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
    user = _identity(request)
    odometer = float(body.get("odometer") or 0.0)
    liters = float(body.get("liters") or 0.0)
    rate = float(body.get("rate") or 0.0)
    # Fueling state the driver picks for this purchase (e.g. MP when a UP truck
    # refuels in Madhya Pradesh). Drives the fuel band below; falls back to the
    # trip's state when omitted.
    state_code = str(body.get("state_code") or "").strip().upper() or None

    if exp_type not in JSON_EXPENSE_TYPES:
        return _bad("invalid expense type", "INVALID_EXPENSE_TYPE")

    with get_db() as conn:
        trip = get_trip_by_code(conn, trip_code)
        if trip is None:
            return _not_found("trip not active")
        if _trip_forbidden(conn, user, trip):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        if trip_status(conn, trip_code) != "ACTIVE":
            return _not_found("trip not active")
        if exp_type in AUTO_LEDGER_TYPES:
            # Auto-posted entries (CASH_ADVANCE / DRIVER_SALARY) bypass the
            # rule/flag pipeline: fixed-provision rows are always Approved.
            verdict = None
            manager_status = "APPROVED"
            is_flagged = False
            flag_reason = None
        else:
            # Resolve the per-state fuel band. The driver-submitted `state_code`
            # (fueling state) takes precedence; fall back to the trip's operating
            # state, then the global default band. This way a UP truck refueling
            # in MP is judged against MP's benchmark, not its home state.
            band = DEFAULT_BAND
            band_state = state_code or (trip or {}).get("state_code")
            if band_state:
                benchmark = get_benchmark_price_and_tolerance(conn, band_state)
                if benchmark is not None:
                    price, tol_fraction = benchmark
                    band = derive_band(price, tol_fraction)
            verdict = evaluate_expense(
                RuleInput(
                    exp_type=exp_type,
                    amount=amount,
                    liters=liters,
                    rate=rate,
                    odometer=odometer,
                    band=band,
                    band_state_code=band_state,
                )
            )
            manager_status = "PENDING" if verdict.flagged or exp_type in GOODS_TYPES else "APPROVED"
            is_flagged = bool(verdict.flagged)
            flag_reason = verdict.reason or None
        insert_expense(
            conn,
            trip_code=trip_code,
            exp_type=exp_type,
            amount=amount,
            liters=liters,
            rate=rate,
            odometer=odometer,
            is_flagged=is_flagged,
            flag_reason=flag_reason,
            manager_status=manager_status,
            state_code=state_code,
        )
        if odometer > 0:
            update_trip_odometer(conn, trip_code, odometer)
    return _created(
        {
            "accepted": True,
            "trip_code": trip_code,
            "exp_type": exp_type,
            "manager_status": manager_status,
            "is_flagged": is_flagged,
            "flag_reason": flag_reason,
        }
    )


@router.post("/expenses/{expense_id}/action", response_model=Data[ExpenseActionResult])
async def api_action_expense(request: Request, expense_id: int):
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    action = str((body or {}).get("action", "")).upper()
    if action not in ("APPROVE", "REJECT"):
        return _bad("action must be APPROVE or REJECT", "INVALID_ACTION")
    status = "APPROVED" if action == "APPROVE" else "REJECTED"

    with get_db() as conn:
        expense_code = get_expense_trip_code(conn, expense_id)
        if not expense_code:
            return _not_found("expense not found")
        trip = get_trip_by_code(conn, expense_code)
        if trip is None or _trip_forbidden(conn, user, trip):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        trip_code = action_expense_status(conn, expense_id, status)
        # Resolve the driver phone for WhatsApp notification (best-effort).
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT phone FROM users WHERE id = %s",
                (trip.get("driver_user_id"),),
            )
            driver_row = cur.fetchone()
        except Exception:
            driver_row = None
        driver_phone = (driver_row or {}).get("phone") if driver_row else None

        # Human-facing status labels (bilingual).
        label_en = "Approved" if status == "APPROVED" else "Deducted"
        label_hi = "स्वीकृत" if status == "APPROVED" else "कटौती"

        # Best-effort WhatsApp notification to the driver.
        if driver_phone:
            try:
                import requests as _req
                _req.post(
                    f"{request.url.scheme}://{request.url.netloc}/api/v1/whatsapp/send",
                    json={
                        "to": driver_phone,
                        "template": "expense_action",
                        "params": {
                            "trip_code": trip_code,
                            "expense_id": expense_id,
                            "action_en": label_en,
                            "action_hi": label_hi,
                        },
                    },
                    timeout=5,
                )
            except Exception:
                pass  # Notification is best-effort, never block the API response.

    return _ok({
        "expense_id": expense_id,
        "status": status,
        "trip_code": trip_code,
        "label_en": label_en,
        "label_hi": label_hi,
    })