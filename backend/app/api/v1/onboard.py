from __future__ import annotations

"""Transactional transport-firm onboarding wizard.

A Super Admin creates a whole transport firm — fleet, owner Trip Manager,
trial subscription, and optionally a first vehicle + driver — in ONE atomic
request. This collapses the previously-fragile multi-step manual flow (G2) and
makes subscription choice inline with onboarding.
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.password import hash_password
from backend.app.core.security import require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    fleet_phone_exists,
    get_fleet_email_context,
    get_fleet_entitlement,
    insert_fleet,
    log_fleet_billing_event,
    start_trial_subscription,
)
from backend.app.db.queries.users import create_user
from backend.app.db.queries.vehicles import insert_vehicle, vehicle_number_exists
from backend.app.services.email.client import (
    manager_onboarding_email_context,
    send_manager_onboarding_email_sync,
)
from backend.app.schemas.api_v1 import Data

from backend.app.api.v1.deps import _bad, _created, _identity, _read_json_body

import re as _re

router = APIRouter(prefix="/api/v1")
_PLATE_RE = _re.compile(settings.plate_regex)

_VALID_PLANS = ("TRIAL", "MONTHLY", "YEARLY")


def _login_url(request: Request) -> str:
    """Derive the web login URL for the manager onboarding email."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/login"


@router.post("/fleets/onboard", response_model=Data[dict[str, Any]])
async def api_onboard_fleet(request: Request):
    """Create a transport firm + owner manager + trial in one transaction."""
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    actor = _identity(request)
    body = await _read_json_body(request)

    fleet_c = body.get("fleet") or {}
    owner_c = body.get("owner") or {}
    plan_code = str(body.get("plan_code", "TRIAL")).upper()

    owner_name = str(fleet_c.get("owner_name", "")).strip()
    phone = str(fleet_c.get("phone", "")).strip()
    email = ((fleet_c.get("email") or "")).strip() or None

    username = str(owner_c.get("username", "")).strip()
    full_name = str(owner_c.get("full_name", "")).strip()
    password = str(owner_c.get("password", "")).strip()
    owner_email = ((owner_c.get("email") or "")).strip() or email

    if not owner_name or not phone:
        _bad("fleet.owner_name and fleet.phone are required", "MISSING_FIELDS")
    if not username or not full_name or not password:
        _bad("owner.username, full_name and password are required", "MISSING_FIELDS")
    if plan_code not in _VALID_PLANS:
        _bad("unknown plan_code", "INVALID_PLAN")

    vehicle = body.get("initial_vehicle") or {}
    driver = body.get("initial_driver") or {}

    from backend.app.services.billing.razorpay import (
        MONTHLY_PRICE,
        YEARLY_PRICE,
        create_payment_link,
    )
    from backend.app.services.entitlements import fleet_can_add_vehicles

    with get_db() as conn:
        if fleet_phone_exists(conn, phone):
            return JSONResponse(
                status_code=409,
                content={"error": "fleet with this phone exists", "code": "DUP_PHONE"},
            )
        fleet_id = insert_fleet(conn, owner_name, phone, email)
        start_trial_subscription(conn, fleet_id)
        log_fleet_billing_event(
            conn, fleet_id, "TRIAL_START", plan_code="TRIAL",
            payload={"onboard": True}, created_by=actor.get("user_id"),
        )
        actor_id = actor.get("user_id")
        owner_user_id = create_user(
            conn, username, hash_password(password), full_name, "trip_manager",
            phone, owner_email, created_by=actor_id, fleet_id=fleet_id,
        )
        vehicle_id = None
        vehicle_no = str(vehicle.get("vehicle_number", "")).strip().upper()
        if vehicle_no and not vehicle_number_exists(conn, vehicle_no) \
                and _PLATE_RE.match(vehicle_no):
            ent = get_fleet_entitlement(conn, fleet_id)
            allowed, _r = fleet_can_add_vehicles(conn, fleet_id, ent)
            if allowed:
                vehicle_id = insert_vehicle(
                    conn, vehicle_no,
                    (vehicle.get("make_model") or "").strip() or None,
                    float(vehicle.get("tank_capacity_liters", 350.0)),
                    float(vehicle.get("expected_km_per_liter", 4.0)),
                    ((vehicle.get("owner_phone") or "")).strip() or None,
                    created_by=actor_id, fleet_id=fleet_id,
                )

        driver_user_id = None
        d_username = str(driver.get("username", "")).strip()
        d_full = str(driver.get("full_name", "")).strip()
        d_pass = str(driver.get("password", "")).strip()
        if d_username and d_full and d_pass:
            driver_user_id = create_user(
                conn, d_username, hash_password(d_pass), d_full, "driver",
                ((driver.get("phone") or "")).strip() or None,
                ((driver.get("email") or "")).strip() or None,
                created_by=actor_id, fleet_id=fleet_id,
                batta_type=driver.get("batta_type"),
                default_batta_rate=driver.get("default_batta_rate"),
            )

        # Fire the welcome email so a freshly-onboarded manager (who supplied an
        # email) immediately receives their credentials, matching Path A.
        email_queued = False
        manager_email = ((owner_email or "")).strip()
        if owner_user_id and manager_email:
            fleet_row = get_fleet_email_context(conn, fleet_id)
            if fleet_row is not None:
                ctx = manager_onboarding_email_context(
                    manager_full_name=full_name,
                    manager_username=username,
                    temporary_password=password,
                    fleet=fleet_row,
                    login_url=_login_url(request),
                )
                ctx["to_email"] = manager_email
                sent = send_manager_onboarding_email_sync(**ctx)
                email_queued = bool(sent.get("queued")) or sent.get("status") == "sent"

        payment_url = None
        if plan_code != "TRIAL":
            price = MONTHLY_PRICE if plan_code == "MONTHLY" else YEARLY_PRICE
            label = "Monthly" if plan_code == "MONTHLY" else "Yearly"
            try:
                link = create_payment_link(
                    price,
                    {"name": owner_name, "contact": phone, "email": email},
                    f"VK {label} Plan",
                    reference_id=f"fleet_{fleet_id}_{plan_code.lower()}",
                )
                payment_url = link.get("short_url") or link.get("long_url")
            except Exception:  # noqa: BLE001 — payment is non-blocking
                payment_url = None

    return _created(
        {
            "fleet_id": fleet_id,
            "owner_user_id": owner_user_id,
            "vehicle_id": vehicle_id,
            "driver_user_id": driver_user_id,
            "plan_code": plan_code,
            "payment_url": payment_url,
            "email_queued": email_queued,
        }
    )
