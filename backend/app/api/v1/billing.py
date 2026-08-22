from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import _bad, _identity, _ok, _read_json_body
from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    get_all_fleets,
    get_all_plans,
    get_default_fleet,
    get_fleet_billing_events,
    get_fleet_by_id,
    get_fleet_entitlement,
    log_fleet_billing_event,
    start_trial_subscription,
)
from backend.app.db.queries.users import get_user_fleet_id
from backend.app.schemas.api_v1 import (
    BillingOverview,
    BillingSubscribeResult,
    BillingVehicleSlotResult,
    Data,
)
from backend.app.services.billing.razorpay import (
    VEHICLE_SLOT_PRICE,
    create_payment_link,
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


def _plan_price(plan: dict) -> float:
    """Safe numeric price from a subscription_plans row."""
    try:
        return float(plan.get("price") or 0)
    except (TypeError, ValueError):
        return 0.0

@router.get("/billing/overview", response_model=Data[BillingOverview])
def api_billing_overview(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    with get_db() as conn:
        fleet = _billing_fleet(conn, user.get("user_id"))
        ent = get_fleet_entitlement(conn, fleet["id"]) if fleet else None
        plans = get_all_plans(conn)
    plan_cards = []
    for p in plans:
        code = p.get("code", "")
        plan_cards.append({
            "code": code,
            "name": p.get("name", code),
            "price": int(_plan_price(p)),
            "period": p.get("billing_cycle", "MONTHLY"),
            "vehicle_limit": int(p.get("vehicle_limit") or 1),
            "trial_days": int(p.get("trial_days") or 0),
            "description": p.get("name", ""),
        })
    fleet_info = {
        "name": (fleet or {}).get("owner_name", "Your Fleet"),
        "id": (fleet or {}).get("id"),
        "subscription_status": (ent or {}).get("subscription_status", "?"),
        "plan_code": (ent or {}).get("plan_code", ""),
        "vehicle_count": (ent or {}).get("vehicle_count", 0),
        "vehicle_limit": (ent or {}).get("vehicle_limit", 1),
        "vehicle_slot_price": int(VEHICLE_SLOT_PRICE),
        "trial_ends_at": (fleet or {}).get("trial_ends_at"),
        "next_billing_date": (fleet or {}).get("next_billing_date"),
    }
    return _ok({
        "fleet": fleet_info,
        "plans": plan_cards,
    })


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
            log_fleet_billing_event(
                conn, fleet["id"], "TRIAL_START", plan_code="TRIAL",
                created_by=user.get("user_id"),
            )
            return _ok({"redirect_url": "/fleets", "activated": True, "trial": True})
        if plan_code not in ("MONTHLY", "YEARLY"):
            return _bad("unknown plan_code", "INVALID_PLAN")
        # Resolve price from the seeded catalogue (single source of truth)
        from backend.app.db.queries.fleets import get_plan_by_code
        plan = get_plan_by_code(conn, plan_code)
        price = _plan_price(plan) if plan else (799.00 if plan_code == "MONTHLY" else 7191.00)
        cust = {
            "name": fleet.get("owner_name", ""),
            "contact": fleet.get("phone", ""),
            "email": fleet.get("email", ""),
        }
        ref = f"fleet_{fleet['id']}_{plan_code.lower()}"
        desc = f"VK {plan_code.title()} Plan"
    try:
        link = create_payment_link(price, cust, desc, reference_id=ref)
    except Exception as exc:  # noqa: BLE001
        return _bad(f"payment link failed: {exc}", "PAYMENT_LINK_FAILED")
    url = link.get("short_url") or link.get("long_url")
    with get_db() as conn:
        log_fleet_billing_event(
            conn, fleet["id"], "SUBSCRIBE", plan_code=plan_code,
            payload={"reference_id": ref, "amount": price},
            razorpay_ref=link.get("id"),
            amount=price,
            created_by=user.get("user_id"),
        )
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
        ref = f"fleet_{fleet['id']}_vehicle_slot"
    try:
        link = create_payment_link(
            VEHICLE_SLOT_PRICE,
            cust,
            "VK Extra Vehicle Slot",
            reference_id=ref,
        )
    except Exception as exc:  # noqa: BLE001
        return _bad(f"payment link failed: {exc}", "PAYMENT_LINK_FAILED")
    url = link.get("short_url") or link.get("long_url")
    with get_db() as conn:
        log_fleet_billing_event(
            conn, fleet["id"], "EXTRA_SLOT",
            payload={"reference_id": ref, "amount": int(VEHICLE_SLOT_PRICE)},
            razorpay_ref=link.get("id"),
            amount=int(VEHICLE_SLOT_PRICE),
            created_by=user.get("user_id"),
        )
    return _ok({"redirect_url": url, "payment_link": link})


# ── Renew ────────────────────────────────────────────────────────────────

@router.post("/billing/renew/{plan_code}", response_model=Data[BillingSubscribeResult])
async def api_billing_renew(request: Request, plan_code: str):
    """Renew an existing subscription (creates Razorpay payment link)."""
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = _identity(request)
    plan_code = plan_code.upper()
    if plan_code not in ("MONTHLY", "YEARLY", "TRIAL"):
        return _bad("unknown plan_code for renewal", "INVALID_PLAN")

    with get_db() as conn:
        fleet = _billing_fleet(conn, user.get("user_id"))
        if fleet is None:
            return _bad("no fleet associated with this account")
        if plan_code == "TRIAL":
            start_trial_subscription(conn, fleet["id"])
            log_fleet_billing_event(
                conn, fleet["id"], "RENEW_TRIAL", plan_code="TRIAL",
                created_by=user.get("user_id"),
            )
            return _ok({"redirect_url": "/fleets", "activated": True, "trial": True})
        from backend.app.db.queries.fleets import get_plan_by_code
        plan = get_plan_by_code(conn, plan_code)
        price = _plan_price(plan) if plan else (799.00 if plan_code == "MONTHLY" else 7191.00)
        cust = {
            "name": fleet.get("owner_name", ""),
            "contact": fleet.get("phone", ""),
            "email": fleet.get("email", ""),
        }
        ref = f"fleet_{fleet['id']}_{plan_code.lower()}"
        desc = f"VK {plan_code.title()} Renewal"
    try:
        link = create_payment_link(price, cust, desc, reference_id=ref)
    except Exception as exc:  # noqa: BLE001
        return _bad(f"payment link failed: {exc}", "PAYMENT_LINK_FAILED")
    url = link.get("short_url") or link.get("long_url")
    with get_db() as conn:
        log_fleet_billing_event(
            conn, fleet["id"], "RENEW", plan_code=plan_code,
            payload={"reference_id": ref, "amount": price},
            razorpay_ref=link.get("id"),
            amount=price,
            created_by=user.get("user_id"),
        )
    return _ok({"redirect_url": url, "payment_link": link})


# ── Super Admin: all-fleet subscription table ────────────────────────────

@router.get("/fleets/subscriptions", response_model=Data[list[dict]])
def api_fleets_subscriptions(request: Request):
    """Super Admin consolidated view: all fleets with plan & subscription info."""
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        fleets = get_all_fleets(conn)
        plans = {p["id"]: p for p in get_all_plans(conn)} if fleets else {}
        result = []
        for f in fleets:
            fid = f.get("id")
            plan_id = f.get("plan_id")
            plan = plans.get(plan_id, {})
            result.append({
                "fleet_id": fid,
                "owner_name": f.get("owner_name", ""),
                "phone": f.get("phone", ""),
                "email": f.get("email", ""),
                "subscription_status": f.get("subscription_status", "?"),
                "plan_code": f.get("plan_code") or plan.get("code", ""),
                "plan_name": f.get("plan_name") or plan.get("name", ""),
                "vehicle_count": f.get("vehicle_count", 0),
                "vehicle_limit": f.get("vehicle_limit", 1),
                "trial_ends_at": f.get("trial_ends_at"),
                "next_billing_date": f.get("next_billing_date"),
                "is_active": f.get("is_active", True),
                "entitlement_addons": f.get("entitlement_addons"),
                # Must stay INSIDE the `with` block: get_db() closes the
                # connection on exit, and executing on a closed psycopg2
                # connection raises InterfaceError (500).
                "recent_events": get_fleet_billing_events(conn, fid, limit=5),
            })
    return _ok(result)
