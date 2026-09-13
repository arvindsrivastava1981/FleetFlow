"""Self-serve fleet onboarding for fleet-less trip_managers.

The super-admin-only ``/fleets/onboard`` wizard was removed — fleet creation
now flows exclusively through the self-serve ``/fleets/self-onboard`` path
(called from the SPA onboarding wizard or triggered at registration time).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.api.v1.deps import _bad, _created, _read_json_body
from backend.app.core.security import get_current_user, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    get_fleet_by_id,
    insert_fleet,
    log_fleet_billing_event,
)
from backend.app.db.queries.users import get_user_by_id
from backend.app.schemas.api_v1 import Data

router = APIRouter(prefix="/api/v1")


def _not_found(message: str, code: str = "NOT_FOUND") -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": message, "code": code})


@router.post("/fleets/self-onboard", response_model=Data[dict])
async def api_self_onboard_fleet(request: Request):
    """Self-serve fleet creation for fleet-less trip_managers.

    Any authenticated ``trip_manager`` without a ``fleet_id`` may create their
    own transport firm in one transaction: a fleet starting the 15-day TRIAL
    plan plus binding the caller as its owner (``fleet_role = 'owner'``).
    Users who already have a fleet get 409.
    """
    guard = require_json_role(request, "trip_manager")
    if guard is not None:
        return guard
    actor = get_current_user(request)
    body = await _read_json_body(request)

    owner_name = str(body.get("owner_name", "")).strip()
    phone = str(body.get("phone", "")).strip()
    email = (str(body.get("email", "")).strip() or None) or None

    if not owner_name or not phone:
        return _bad("owner_name and phone are required", "MISSING_FIELDS")

    with get_db() as conn:
        row = get_user_by_id(conn, actor["user_id"])
        if row is None:
            return _not_found("user not found")
        if row.get("fleet_id"):
            return _bad("user already belongs to a fleet", "ALREADY_ONBOARDED")
        fleet_id = insert_fleet(conn, owner_name, phone, email)
        conn.cursor().execute(
            "UPDATE users SET fleet_id = %s, fleet_role = 'owner' WHERE id = %s",
            (fleet_id, actor["user_id"]),
        )
        log_fleet_billing_event(
            conn, fleet_id, "TRIAL_START", "TRIAL", {"self_onboarded": True},
            created_by=actor["user_id"],
        )
        fleet = get_fleet_by_id(conn, fleet_id)

    return _created(
        {
            "fleet_id": fleet_id,
            "plan_code": "TRIAL",
            "trial_ends_at": (
                fleet["trial_ends_at"].isoformat() if fleet and fleet.get("trial_ends_at") else None
            ),
        }
    )
