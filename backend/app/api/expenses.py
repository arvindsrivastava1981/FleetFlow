"""Expenses router — WhatsApp-simulation logging + manager approval action.

Fixes from deep_agent_recommendation:
- §2.1 unauthenticated mutations: both endpoints guard via `require_auth`
  (`/simulate-whatsapp` and `/action-expense` -> 303 to /login).
- §2.5/§2.8: uses the pure `evaluate_expense` engine (benchmark-derived band,
  prev-odo from any expense type).
- §2.7: `insert_expense` now resolves & persists `expenses.trip_id`.
- §3.5: `exp_type` whitelisted via the System Invariants enum.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from backend.app.core.security import require_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.expenses import action_expense_status, insert_expense
from backend.app.db.queries.trips import trip_status
from backend.app.services.rules.constants import GOODS_TYPES
from backend.app.services.rules.evaluate import RuleInput, evaluate_expense

router = APIRouter()

EXPENSE_TYPES: tuple[str, ...] = (
    "FUEL", "TOLL", "REPAIR", "OTHER", "CHALLAN", "MISC",
    "RTO-FINE", "DEF", "GOODS_BUY", "GOODS_SALE",
)


@router.post("/simulate-whatsapp")
def simulate_whatsapp(
    request: Request,
    trip_code: str = Form(...),
    exp_type: str = Form(...),
    amount: float = Form(...),
    odometer: float = Form(0.0),
    liters: float = Form(0.0),
    rate: float = Form(0.0),
):
    guard = require_auth(request)
    if guard is not None:
        return guard

    exp_type = exp_type.upper()
    if exp_type not in EXPENSE_TYPES:
        return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

    with get_db() as conn:
        status = trip_status(conn, trip_code)
        if status != "ACTIVE":
            return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

        verdict = evaluate_expense(
            RuleInput(
                exp_type=exp_type,
                amount=amount,
                liters=liters,
                rate=rate,
                odometer=odometer,
            )
        )
        manager_status = (
            "PENDING"
            if verdict.flagged or exp_type in GOODS_TYPES
            else "APPROVED"
        )
        insert_expense(
            conn,
            trip_code=trip_code.strip().upper(),
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
                "UPDATE trips SET current_odo = GREATEST(current_odo, %s) "
                "WHERE trip_code = %s",
                (odometer, trip_code),
            )
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)


@router.get("/action-expense")
def action_expense(request: Request, id: int, action: str):
    guard = require_auth(request)
    if guard is not None:
        return guard

    status = "APPROVED" if action == "APPROVE" else "REJECTED"
    with get_db() as conn:
        trip_code = action_expense_status(conn, id, status)
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)