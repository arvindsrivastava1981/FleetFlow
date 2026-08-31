"""In-app notification feed (feature F-3) — derived live, nothing stored."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import _identity, _ok
from backend.app.core.security import require_json_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.notifications import (
    drivers_licence_expiring,
    fleet_trial_ending,
    pending_approvals,
    settlement_ready_count,
)

router = APIRouter(prefix="/api/v1")


@router.get("/notifications")
def api_notifications(request: Request):
    """Computed alert feed for the signed-in user (audit F-3).

    Super admins see the fleet-wide picture; trip managers only their own
    slice. Nothing is persisted — items are derived from the ledger on read.
    """
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    scope_id = user.get("user_id") if user.get("role") == "trip_manager" else None

    items: list[dict] = []
    with get_db() as conn:
        for row in pending_approvals(conn, scope_id):
            items.append(
                {
                    "type": "pending_approval",
                    "title": f"{row['exp_type']} awaiting approval",
                    "detail": (
                        f"₹{float(row['amount']):,.0f} · {row['trip_code']} "
                        f"({row['vehicle_no']}) — waiting more than 24h"
                    ),
                }
            )
        for row in drivers_licence_expiring(conn, scope_id):
            expired = row["licence_expiry"] < date.today()
            items.append(
                {
                    "type": "licence_expiry",
                    "title": (
                        f"{row['full_name']}'s licence expired"
                        if expired
                        else f"{row['full_name']}'s licence expiring soon"
                    ),
                    "detail": (
                        f"Licence {'expired' if expired else 'expires'} "
                        f"{row['licence_expiry'].isoformat()} — renew before "
                        f"the next dispatch ({row['email']})."
                    ),
                }
            )
        trial = fleet_trial_ending(conn, user.get("user_id"))
        if trial:
            items.append(
                {
                    "type": "trial_ending",
                    "title": "Trial ending soon",
                    "detail": (
                        f"Fleet “{trial['owner_name']}” trial ends "
                        f"{trial['trial_ends_at'].isoformat()[:10]} — pick a plan "
                        f"on the Subscription page."
                    ),
                }
            )
        ready = settlement_ready_count(conn, scope_id)
        if ready:
            items.append(
                {
                    "type": "settlement_ready",
                    "title": "Trips ready to settle",
                    "detail": f"{ready} active trip(s) have no pending expenses.",
                }
            )
    return _ok(items[:25])

