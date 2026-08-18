"""Billing router — Razorpay Payment Links + webhook.

GET  /billing/upgrade      — monthly (799) or yearly (7191) plan
POST /billing/subscribe    — payment link, redirect to Razorpay
POST /billing/webhook      — payment_link.paid, activate plan or bump limit
GET  /billing/vehicle-slot — upsell page
POST /billing/vehicle-slot — one-time payment link
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.security import (
    esc, get_current_user, require_auth, verify_razorpay_webhook,
)
from backend.app.db.connection import get_db
from backend.app.db.queries.billing import (
    mark_webhook_processed, webhook_already_processed,
)
from backend.app.db.queries.fleets import (
    bump_vehicle_limit, get_fleet_by_id, get_fleet_entitlement,
    set_plan_subscription, set_yearly_subscription, start_trial_subscription,
)
from backend.app.db.queries.users import get_user_fleet_id
from backend.app.services.billing.razorpay import (
    MONTHLY_PRICE, YEARLY_PRICE, VEHICLE_SLOT_PRICE, create_payment_link,
)
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()


def _resolve_fleet(conn, user_id: int) -> dict | None:
    fid = get_user_fleet_id(conn, user_id)
    if not fid:
        from backend.app.db.queries.fleets import get_default_fleet
        default = get_default_fleet(conn)
        fid = default["id"] if default else None
    if not fid:
        return None
    return get_fleet_by_id(conn, fid)


def _cust_info(f: dict) -> dict:
    return {"name": f.get("owner_name",""), "contact": f.get("phone",""), "email": f.get("email","")}
@router.get("/billing/upgrade", response_class=HTMLResponse)
def upgrade_page(request: Request):
    guard = require_auth(request)
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        fleet = _resolve_fleet(conn, user.get("user_id"))
        ent = get_fleet_entitlement(conn, fleet["id"]) if fleet else None
    fname = esc(fleet["owner_name"]) if fleet else "Your Fleet"
    status = esc((ent or {}).get("subscription_status", "?"))
    plans = "".join(
        f"""<div class="border border-slate-200 rounded-xl p-4 text-center">
<p class="font-extrabold text-lg">{n}</p><p class="text-xs text-slate-500 mb-2">{d}</p>
<form method="post" action="/billing/subscribe">
<input type="hidden" name="plan_code" value="{c}">
<button class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-6 py-2.5 rounded-xl text-sm">{b}</button>
</form></div>"""
        for c, n, d, b in [
            ("TRIAL", "Trial Pack",
             "15 days for free \u00b7 1 vehicle", "Start Trial"),
            ("MONTHLY", "Monthly \u20b9{:,}".format(int(MONTHLY_PRICE)),
             "1 vehicle \u00b7 \u20b9{:,}/mo".format(int(MONTHLY_PRICE)), "Pay Now"),
            ("YEARLY", "Yearly \u20b9{:,}".format(int(YEARLY_PRICE)),
             "1 vehicle \u00b7 \u20b9{:,}/yr (25% off)".format(int(YEARLY_PRICE)), "Pay Now"),
        ]
    )
    uname = user.get("username", "")
    role = user.get("role", "")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Upgrade</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-7xl mx-auto space-y-6">
{render_header(authenticated=True, username=uname, role=role)}
<div class="flex flex-col lg:flex-row gap-4 items-start">
{render_sidebar("billing", role)}
<main class="flex-1 min-w-0 w-full space-y-4">
<h2 class="text-lg font-extrabold">Upgrade Subscription</h2>
<div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm max-w-2xl">
<p class="text-sm mb-4">Fleet: <strong>{fname}</strong> &middot; Status: <strong>{status}</strong></p>
<p class="text-xs text-slate-500 mb-6">Trial ended. Pick a plan.</p>
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">{plans}</div>
</div>
</main>
</div>
{render_footer()}
</div></body></html>"""
@router.post("/billing/subscribe")
def subscribe(request: Request, plan_code: str = Form(...)):
    guard = require_auth(request)
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        fleet = _resolve_fleet(conn, user.get("user_id"))
        if not fleet:
            return HTMLResponse("<h2>No fleet</h2>", status_code=400)
        cust = _cust_info(fleet)
    fid = fleet["id"]
    if plan_code == "TRIAL":
        with get_db() as conn:
            start_trial_subscription(conn, fid)
        return RedirectResponse(url="/vehicles", status_code=303)
    if plan_code == "YEARLY":
        amount, desc, ref = YEARLY_PRICE, "VK Yearly Rs.7191 (25% off)", f"fleet_{fid}_yearly"
    else:
        amount, desc, ref = MONTHLY_PRICE, "VK Monthly Rs.799", f"fleet_{fid}_monthly"
    try:
        link = create_payment_link(amount, cust, desc, reference_id=ref)
    except Exception:
        return HTMLResponse("<h2>Payment link failed. Check creds.</h2>", status_code=500)
    url = link.get("short_url") or link.get("long_url")
    if url:
        return RedirectResponse(url=url, status_code=303)
    return HTMLResponse(f"<pre>{link}</pre>")
@router.get("/billing/vehicle-slot", response_class=HTMLResponse)
def vehicle_slot_page(request: Request):
    guard = require_auth(request)
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        fleet = _resolve_fleet(conn, user.get("user_id"))
        ent = get_fleet_entitlement(conn, fleet["id"]) if fleet else None
    fname = esc(fleet["owner_name"]) if fleet else "Your Fleet"
    limit = (ent or {}).get("vehicle_limit", 1)
    uname = user.get("username", "")
    role = user.get("role", "")
    p = int(VEHICLE_SLOT_PRICE)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Buy Slot</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-7xl mx-auto space-y-6">
{render_header(authenticated=True, username=uname, role=role)}
<div class="flex flex-col lg:flex-row gap-4 items-start">
{render_sidebar("billing", role)}
<main class="flex-1 min-w-0 w-full space-y-4">
<h2 class="text-lg font-extrabold">Vehicle Limit Reached</h2>
<div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4 max-w-2xl">
<p class="text-sm">Fleet <strong>{fname}</strong> limit: <strong>{limit}</strong>.</p>
<p class="text-xs text-slate-500">Purchase an additional vehicle slot.</p>
<div class="bg-sky-50 border border-sky-200 rounded-xl p-4 text-center">
<p class="text-2xl font-extrabold text-sky-800">\u20b9{p:,}</p>
<form method="post" action="/billing/vehicle-slot" class="mt-3">
<button class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-6 py-2.5 rounded-xl text-sm">Buy Slot</button></form>
</div>
</div>
</main>
</div>
{render_footer()}
</div></body></html>"""


@router.post("/billing/vehicle-slot")
def buy_vehicle_slot(request: Request):
    guard = require_auth(request)
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        fleet = _resolve_fleet(conn, user.get("user_id"))
        if not fleet:
            return HTMLResponse("<h2>No fleet</h2>", status_code=400)
        cust = _cust_info(fleet)
    fid = fleet["id"]
    try:
        link = create_payment_link(
            VEHICLE_SLOT_PRICE, cust, "VK Extra Vehicle Slot",
            reference_id=f"fleet_{fid}_vehicle_slot")
        url = link.get("short_url") or link.get("long_url")
        return RedirectResponse(url=url, status_code=303) if url else HTMLResponse(f"<pre>{link}</pre>")
    except Exception:
        return HTMLResponse("<h2>Payment link failed</h2>", status_code=500)
@router.post("/billing/webhook")
async def billing_webhook(request: Request):
    """Razorpay server-to-server webhook — signature verified, no auth."""
    body = await request.body()
    sig = request.headers.get("x-razorpay-signature")
    ts = request.headers.get("x-razorpay-event-timestamp")
    if not verify_razorpay_webhook(body, sig, ts):
        return HTMLResponse("invalid signature", status_code=403)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return HTMLResponse("bad json", status_code=400)
    event = payload.get("event", "")
    if event != "payment_link.paid":
        return HTMLResponse("ok", status_code=200)
    # Razorpay stable event id — used to dedupe retried deliveries.
    event_id = (payload.get("payload", {}).get("payment_link", {})
                .get("entity", {}).get("id", ""))
    link = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
    ref = link.get("reference_id", "")
    parts = ref.split("_")  # fleet_<id>_<action>
    if len(parts) < 3 or parts[0] != "fleet":
        return HTMLResponse("ok", status_code=200)
    try:
        fid = int(parts[1])
        action = "_".join(parts[2:])
    except (ValueError, IndexError):
        return HTMLResponse("ok", status_code=200)
    with get_db() as conn:
        # Idempotency guard: if this event was already applied, skip it so a
        # retried delivery cannot activate/bump the fleet twice.
        if not event_id or webhook_already_processed(conn, event_id):
            return HTMLResponse("ok", status_code=200)
        if action == "monthly":
            set_plan_subscription(conn, fid, "MONTHLY")
        elif action == "yearly":
            set_yearly_subscription(conn, fid)
        elif action == "vehicle_slot":
            bump_vehicle_limit(conn, fid)
        # Log inside the same transaction as the side effect: commit is atomic.
        mark_webhook_processed(conn, event_id, event, payload)
    return HTMLResponse("ok", status_code=200)

