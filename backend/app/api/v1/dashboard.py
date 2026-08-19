"""Role-aware dashboard `/api/v1` router (single endpoint)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.core.security import require_json_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.dashboards import (
    active_trip_progress,
    admin_kpis,
    approved_cash_net,
    driver_today_logged,
    manager_kpis,
    open_escalations,
)
from backend.app.db.queries.trips import get_active_trip_for_driver

from backend.app.api.v1.deps import _identity, _jsonable, _ok
from backend.app.schemas.api_v1 import DashboardOverview, Data

router = APIRouter(prefix="/api/v1")


@router.get("/dashboard/overview", response_model=Data[DashboardOverview])
def api_dashboard_overview(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = _identity(request)
    role = user.get("role", "")
    user_id = user.get("user_id")

    with get_db() as conn:
        if role == "super_admin":
            data = {"role": role, "kpis": admin_kpis(conn)}
        elif role == "trip_manager":
            data = {
                "role": role,
                "kpis": manager_kpis(conn, manager_id=user_id),
                "active_trips": active_trip_progress(conn, manager_id=user_id),
                "escalations": open_escalations(conn, limit=20, manager_id=user_id),
            }
        elif role == "driver":
            trip = get_active_trip_for_driver(conn, user_id)
            trip_code = trip["trip_code"] if trip else None
            data = {
                "role": role,
                "trip": _jsonable(trip),
                "today_logged": (
                    driver_today_logged(conn, trip_code) if trip_code else 0.0
                ),
                "cash_in_hand": (
                    (trip["advance_amount"] or 0.0)
                    + approved_cash_net(conn, trip_code)
                    - float(trip.get("driver_batta_amount") or 2500.00)
                )
                if trip_code
                else 0.0,
            }
        else:
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )

    return _ok(_jsonable(data))