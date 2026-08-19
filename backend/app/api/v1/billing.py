"""Billing `/api/v1` router — plan upgrade, trial, and vehicle-slot purchases.

Resolves the caller's fleet, then either activates a TRIAL/MONTHLY/YEARLY plan
(TRIAL is free and applied inline) or builds a Razorpay payment link for
MONTHLY/YEARLY/vehicle-slot and returns its `short_url` for the SPA redirect.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    get_default_fleet,
    get_fleet_by_id,
    get_fleet_entitlement,
    start_trial_subscription,
)
from backend.app.db.queries.users import get_user_fleet_id
from backend.app.services.billing.razorpay import (
    MONTHLY_PRICE,
    YEARLY_PRICE,
    VEHICLE_SLOT_PRICE,
    create_payment_link,
)

from backend.app.api.v1.deps import _bad, _ok, _read_json_body, _identity
from backend.app.schemas.api_v1 import (
    BillingOverview,
    BillingSubscribeResult,
    BillingVehicleSlotResult,
    Data,
)

router = APIRouter(prefix="/api/v1")


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
    user = _identity(request)
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
    return _ok(
        {
            "fleet": {
                "name": (fleet or {}).get("owner_name", "Your Fleet"),
                "id": (fleet or {}).get("id"),
                "subscription_status": (ent or {}).get("subscription_status", "?"),
                "vehicle_count": (ent or {}).get("vehicle_count", 0),
                "vehicle_limit": (ent or {}).get("vehicle_limit", 1),
                "vehicle_slot_price": int(VEHICLE_SLOT_PRICE),
            },
            "plans": plans,
        }
    )


@router.post("/billing/subscribe", response_model=Data[BillingSubscribeResult])
async def api_billing_subscribe(request: Request):
    """Subscribe to a plan; returns a JSON `redirect_url` to Razorpay."""
    guard = require_json_role(request, "trip_manager", "super_admin")
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
            ref, price, desc = (
                f"fleet_{fleet['id']}_monthly", MONTHLY_PRICE, "VK Monthly Plan"
            )
        else:
            ref, price, desc = (
                f"fleet_{fleet['id']}_yearly", YEARLY_PRICE, "VK Yearly Plan"
            )
    try:
        link = create_payment_link(price, cust, desc, reference_id=ref)
    except Exception as exc:  # noqa: BLE001
        return _bad(f"payment link failed: {exc}", "PAYMENT_LINK_FAILED")
    url = link.get("short_url") or link.get("long_url")
    return _ok({"redirect_url": url, "payment_link": link})


@router.post("/billing/vehicle-slot", response_model=Data[BillingVehicleSlotResult])
async def api_billing_vehicle_slot(request: Request):
    """Purchase an extra vehicle slot; returns JSON `redirect_url`."""
    guard = require_json_role(request, "trip_manager", "super_admin")
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