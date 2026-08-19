from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from backend.app.core.security import verify_razorpay_webhook
from backend.app.db.connection import get_db
from backend.app.db.queries.billing import (
    mark_webhook_processed,
    webhook_already_processed,
)
from backend.app.db.queries.fleets import (
    bump_vehicle_limit,
    set_plan_subscription,
    set_yearly_subscription,
)

router = APIRouter()


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