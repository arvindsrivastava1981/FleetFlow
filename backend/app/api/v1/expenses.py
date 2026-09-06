from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.api.v1.deps import _bad, _created, _identity, _not_found, _ok, _trip_forbidden
from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import get_benchmark_price_and_tolerance
from backend.app.db.queries.dashboards import open_escalations_detail
from backend.app.db.queries.expenses import (
    action_expense_status,
    delete_expense,
    get_expense_by_id,
    get_expense_trip_code,
    get_expenses_for_trip,
    insert_expense,
    open_settlement_request,
)
from backend.app.db.queries.trips import (  # noqa: PLC2701 (action owns driver consent stamp)
    driver_consent as record_driver_consent,
)
from backend.app.db.queries.trips import (
    get_trip_by_code,
    trip_status,
    update_trip_odometer,
)
from backend.app.schemas.api_v1 import (
    Data,
    EscalationRow,
    ExpenseAccepted,
    ExpenseActionResult,
)
from backend.app.services.audit.cash import SETTLEMENT_TRANSFER_TYPE, compute_settlement
from backend.app.services.rules.bands import DEFAULT_BAND, derive_band
from backend.app.services.rules.constants import GOODS_TYPES
from backend.app.services.rules.evaluate import RuleInput, evaluate_expense

router = APIRouter(prefix="/api/v1")

JSON_EXPENSE_TYPES: tuple[str, ...] = (
    "FUEL", "DEF", "TOLL", "REPAIR", "CHALLAN", "MISC", "GOODS_BUY", "GOODS_SALE",
    "CASH_ADVANCE", "DRIVER_SALARY", "SETTLEMENT_TRANSFER",
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
    # Phase-1 audit: attribute who keyed the row in. Drivers (bot/app) are the
    # normal channel; trip_manager/super_admin posts are "on behalf of driver".
    entry_source = "MANAGER_MANUAL" if user.get("role") != "driver" else "DRIVER_WHATSAPP"
    odometer = float(body.get("odometer") or 0.0)
    liters = float(body.get("liters") or 0.0)
    rate = float(body.get("rate") or 0.0)
    # Fueling state the driver picks for this purchase (e.g. MP when a UP truck
    # refuels in Madhya Pradesh). Drives the fuel band below; falls back to the
    # trip's state when omitted.
    state_code = str(body.get("state_code") or "").strip().upper() or None
    # Free-text description collected for MISC receipts; stored verbatim in
    # expenses.raw_receipt_text so the manager sees what the money was for.
    raw_receipt_text = str(body.get("raw_receipt_text") or "").strip() or None
    # Optional pump/station name (quick-entry FUEL/DEF card).
    station_name = str(body.get("station_name") or "").strip() or None

    if exp_type not in JSON_EXPENSE_TYPES:
        return _bad("invalid expense type", "INVALID_EXPENSE_TYPE")

    # Audit D-1: a non-positive amount is never a legitimate expense line.
    # The closing SETTLEMENT_TRANSFER amount is recomputed server-side below, so
    # the client-supplied value is ignored (and exempted) for that type only.
    if exp_type != SETTLEMENT_TRANSFER_TYPE and amount <= 0:
        return _bad("amount must be greater than 0", "INVALID_AMOUNT")

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

        # ---- Driver-initiated settlement closing entry (acceptance) ---------
        # A SETTLEMENT_TRANSFER row is the cash-handover record that zeroes the
        # Dr/Cr ledger. While one is PENDING the ledger is locked; a REJECTED
        # request frees it so the driver can log missed expenses and re-initiate.
        live_request = open_settlement_request(conn, trip_code)
        if exp_type == SETTLEMENT_TRANSFER_TYPE:
            if user.get("role") != "driver" or trip.get("driver_user_id") != user.get("user_id"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "only the assigned driver may initiate settlement",
                        "code": "FORBIDDEN",
                    },
                )
            if live_request:
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": "settlement already initiated",
                        "code": "SETTLEMENT_ALREADY_INITIATED",
                    },
                )
            # Server-authoritative amount: the client-supplied value is ignored —
            # the closing entry must equal the live |net_balance|.
            amount = abs(compute_settlement(
                trip, get_expenses_for_trip(conn, trip_code)
            ).net_balance)
        elif live_request:
            return JSONResponse(
                status_code=409,
                content={
                    "error": "ledger locked: settlement initiation awaiting manager action",
                    "code": "SETTLEMENT_LOCKED",
                },
            )

        if exp_type in AUTO_LEDGER_TYPES:
            # Auto-posted entries (CASH_ADVANCE / DRIVER_SALARY) bypass the
            # rule/flag pipeline: fixed-provision rows are always Approved.
            verdict = None
            manager_status = "APPROVED"
            is_flagged = False
            flag_reason = None
        elif exp_type == SETTLEMENT_TRANSFER_TYPE:
            # Closing entries bypass rule evaluation too, but start PENDING —
            # the manager's approval IS what records the driver's acceptance.
            verdict = None
            manager_status = "PENDING"
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
        expense_id = insert_expense(
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
            raw_receipt_text=raw_receipt_text,
            station_name=station_name,
            entry_source=entry_source,
        )
        if odometer > 0:
            update_trip_odometer(conn, trip_code, odometer)
    payload = {
        "accepted": True,
        "expense_id": expense_id,
        "trip_code": trip_code,
        "exp_type": exp_type,
        "manager_status": manager_status,
        "is_flagged": is_flagged,
        "flag_reason": flag_reason,
    }
    if exp_type == SETTLEMENT_TRANSFER_TYPE:
        payload["settlement_amount"] = round(amount, 2)
    return _created(payload)


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
    # Optional manager note explaining a rejection — stored on the row and
    # relayed to the driver in the WhatsApp notification.
    reason = str((body or {}).get("reason") or "").strip() or None
    if reason and len(reason) > 500:
        return _bad("reason must be 500 characters or fewer", "INVALID_REASON")

    with get_db() as conn:
        expense_code = get_expense_trip_code(conn, expense_id)
        if not expense_code:
            return _not_found("expense not found")
        trip = get_trip_by_code(conn, expense_code)
        if trip is None or _trip_forbidden(conn, user, trip):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        row = get_expense_by_id(conn, expense_id)
        # The closing entry gets dedicated wording regardless of the action,
        # so a rejection never reads as a money "deduction".
        is_settlement_row = (
            row is not None
            and row.get("exp_type") == SETTLEMENT_TRANSFER_TYPE
        )
        is_settlement_request = status == "APPROVED" and is_settlement_row
        if is_settlement_request:
            # Re-verify BEFORE flipping status: the PENDING closing entry is
            # excluded by compute_settlement, so net_balance here is the exact
            # figure the driver accepted at initiation time.
            s = compute_settlement(trip, get_expenses_for_trip(conn, expense_code))
            if abs(abs(s.net_balance) - float(row.get("amount") or 0.0)) > 0.01:
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": (
                            "ledger changed since initiation — reject this request "
                            "and ask the driver to re-initiate"
                        ),
                        "code": "LEDGER_CHANGED",
                    },
                )
        trip_code = action_expense_status(conn, expense_id, status, reason=reason)
        if is_settlement_request:
            # The manager's approval records the driver's acceptance on the trip
            # (idempotent, first-wins) so the voucher consent block lights up.
            record_driver_consent(conn, expense_code, row.get("created_by"))
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

        # Human-facing status labels (bilingual). Settlement decisions use
        # dedicated wording so the driver is never told a request was
        # "Deducted" when it was actually declined.
        if is_settlement_row:
            label_en = (
                "Settlement approved"
                if status == "APPROVED"
                else "Settlement request rejected"
            )
            label_hi = (
                "हिसाब स्वीकृत" if status == "APPROVED" else "हिसाब अस्वीकृत"
            )
        else:
            label_en = "Approved" if status == "APPROVED" else "Deducted"
            label_hi = "स्वीकृत" if status == "APPROVED" else "कटौती"

        # Best-effort WhatsApp notification to the driver — Phase C (F-1):
        # direct service call (no self-HTTP hop; resolves B-3/B-9 notes).
        if driver_phone:
            try:
                from backend.app.services.whatsapp.send import send_text

                send_text(
                    driver_phone,
                    f"{label_en} ({label_hi}) · Trip {trip_code} · "
                    f"expense #{expense_id}"
                    + (f"\nReason / कारण: {reason}" if reason else ""),
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


@router.delete("/expenses/{expense_id}", response_model=Data[dict])
async def api_delete_expense(request: Request, expense_id: int):
    """Undo/remove a just-created, manager-entered expense row.

    Quick-entry (ExpenseEntry) shows an "Undo" toast after Save; this endpoint
    permanently deletes that row. Guards:
      - manager-only (trip_manager / super_admin);
      - trip must be in the caller's fleet scope;
      - only rows the manager themselves keyed in (`entry_source == MANAGER_MANUAL`);
      - never auto-posted provisions (CASH_ADVANCE / DRIVER_SALARY) or a
        SETTLEMENT_TRANSFER closing entry (immutable audit records).
    """
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    with get_db() as conn:
        row = get_expense_by_id(conn, expense_id)
        if row is None:
            return _not_found("expense not found")
        exp_type = row.get("exp_type")
        if exp_type in AUTO_LEDGER_TYPES or exp_type == SETTLEMENT_TRANSFER_TYPE:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "provision ledger entries cannot be removed",
                    "code": "CANNOT_DELETE",
                },
            )
        if row.get("entry_source") != "MANAGER_MANUAL":
            return JSONResponse(
                status_code=400,
                content={
                    "error": "only manager-entered expenses can be removed",
                    "code": "CANNOT_DELETE",
                },
            )
        trip = get_trip_by_code(conn, row.get("trip_code") or "")
        if trip is None or _trip_forbidden(conn, user, trip):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        trip_code = delete_expense(conn, expense_id)
    return _ok({
        "deleted": True,
        "expense_id": expense_id,
        "trip_code": trip_code,
    })


@router.delete("/expenses/{expense_id}", response_model=Data[dict])
async def api_delete_expense(request: Request, expense_id: int):
    """Undo/remove a just-created, manager-entered expense row.

    Quick-entry (ExpenseEntry) shows an "Undo" toast after Save; this endpoint
    permanently deletes that row. Guards:
      - manager-only (trip_manager / super_admin);
      - trip must be in the caller's fleet scope;
      - only rows the manager themselves keyed in (`entry_source == MANAGER_MANUAL`);
      - never auto-posted provisions (CASH_ADVANCE / DRIVER_SALARY) or a
        SETTLEMENT_TRANSFER closing entry (immutable audit records).
    """
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    with get_db() as conn:
        row = get_expense_by_id(conn, expense_id)
        if row is None:
            return _not_found("expense not found")
        exp_type = row.get("exp_type")
        if exp_type in AUTO_LEDGER_TYPES or exp_type == SETTLEMENT_TRANSFER_TYPE:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "provision ledger entries cannot be removed",
                    "code": "CANNOT_DELETE",
                },
            )
        if row.get("entry_source") != "MANAGER_MANUAL":
            return JSONResponse(
                status_code=400,
                content={
                    "error": "only manager-entered expenses can be removed",
                    "code": "CANNOT_DELETE",
                },
            )
        trip = get_trip_by_code(conn, row.get("trip_code") or "")
        if trip is None or _trip_forbidden(conn, user, trip):
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )
        trip_code = delete_expense(conn, expense_id)
    return _ok({
        "deleted": True,
        "expense_id": expense_id,
        "trip_code": trip_code,
    })
