"""Trips router — trip creation and settlement.

Fixes from deep_agent_recommendation:
- §2.1 unauthenticated mutations: both endpoints guard via `require_auth`
  (POST /create-trip, GET /settle-trip) -> 303 to /login when unauthenticated.
- §3.5 input validation: plate regex + `+91` phone formats are enforced here
  (the prototype never checked either), plus non-negative advance/odo.
Uses `db/queries/trips.py` for SQL; the `get_db()` contextmanager commits.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from backend.app.core.config import settings
from backend.app.core.security import require_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.trips import (
    active_trip_exists,
    insert_trip,
    pending_expense_count,
    settle_trip as mark_trip_settled,
)

router = APIRouter()

PLATE_RE = re.compile(settings.plate_regex)


@router.post("/create-trip")
def create_trip(
    request: Request,
    trip_code: str = Form(...),
    vehicle_no: str = Form(...),
    driver_name: str = Form(...),
    driver_phone: str = Form(...),
    advance_amount: float = Form(...),
    start_odo: float = Form(...),
):
    guard = require_auth(request)
    if guard is not None:
        return guard

    # ---- Input validation (§3.5) -----------------------------------------
    if advance_amount < 0 or start_odo < 0:
        return RedirectResponse(url="/trips?error=negative", status_code=303)
    if not PLATE_RE.match(vehicle_no.strip().upper()):
        return RedirectResponse(url="/trips?error=plate", status_code=303)
    digits = re.sub(r"\D", "", driver_phone or "")
    if not (digits.startswith("91") and len(digits) == 12):
        return RedirectResponse(url="/trips?error=phone", status_code=303)

    with get_db() as conn:
        if active_trip_exists(conn):
            return RedirectResponse(url="/trips", status_code=303)
        insert_trip(
            conn,
            trip_code.strip().upper(),
            vehicle_no.strip().upper(),
            driver_name.strip(),
            driver_phone.strip(),
            advance_amount,
            start_odo,
        )
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)


@router.get("/settle-trip")
def settle_trip(request: Request, trip_code: str):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        if pending_expense_count(conn, trip_code):
            return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)
        mark_trip_settled(conn, trip_code)
    return RedirectResponse(url="/trips", status_code=303)