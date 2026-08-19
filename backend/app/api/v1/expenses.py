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
from backend.app.db.queries.trips import get_trip_by_code, trip_status, update_trip_odometer
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
)


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
        verdict = evaluate_expense(
            RuleInput(
                exp_type=exp_type,
                amount=amount,
                liters=liters,
                rate=rate,
                odometer=odometer,
            )
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
            update_trip_odometer(conn, trip_code, odometer)
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
    return _ok({"expense_id": expense_id, "status": status, "trip_code": trip_code})