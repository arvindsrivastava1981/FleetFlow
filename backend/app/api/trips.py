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
from backend.app.core.security import get_current_user, require_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import get_default_fleet
from backend.app.db.queries.trips import (
    active_trip_exists,
    get_trip_by_code,
    insert_trip,
    pending_expense_count,
    settle_trip as mark_trip_settled,
)
from backend.app.db.queries.users import get_driver_batta_profile, get_user_fleet_id
from backend.app.services.audit.cash import resolve_trip_batta

router = APIRouter()

PLATE_RE = re.compile(settings.plate_regex)


@router.post("/create-trip")
def create_trip(
    request: Request,
    vehicle_no: str = Form(...),
    driver_name: str = Form(...),
    driver_phone: str = Form(...),
    advance_amount: float = Form(...),
    start_odo: float = Form(...),
    vehicle_id: int | None = Form(None),
    driver_user_id: int | None = Form(None),
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

    user = get_current_user(request) or {}

    with get_db() as conn:
        # Resolve the tenant fleet for the trip (multi-tenant isolation).
        fleet_id = get_user_fleet_id(conn, user.get("user_id")) if user.get("user_id") else None
        if fleet_id is None:
            default = get_default_fleet(conn)
            if default:
                fleet_id = default["id"]
        if fleet_id is None:
            return RedirectResponse(url="/trips?error=no_fleet", status_code=303)

        if active_trip_exists(conn, fleet_id=fleet_id):
            return RedirectResponse(url="/trips", status_code=303)
        driver = get_driver_batta_profile(conn, driver_user_id)
        driver_batta_amount = resolve_trip_batta(driver)
        trip_code = insert_trip(
            conn,
            fleet_id,
            vehicle_no.strip().upper(),
            driver_name.strip(),
            driver_phone.strip(),
            advance_amount,
            start_odo,
            created_by=user.get("user_id"),
            driver_user_id=driver_user_id,
            vehicle_id=vehicle_id,
            driver_batta_amount=driver_batta_amount,
        )
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)


@router.get("/settle-trip")
def settle_trip(request: Request, trip_code: str):
    guard = require_auth(request)
    if guard is not None:
        return guard

    user = get_current_user(request) or {}
    with get_db() as conn:
        trip = get_trip_by_code(conn, trip_code)
        if user.get("role") == "trip_manager" and trip and trip.get("created_by") != user.get("user_id"):
            return RedirectResponse(url="/trips", status_code=303)
        if pending_expense_count(conn, trip_code):
            return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)
        mark_trip_settled(conn, trip_code)
    return RedirectResponse(url="/trips", status_code=303)