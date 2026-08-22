from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.api.v1.deps import _identity, _jsonable, _ok
from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.dashboards import (
    active_trip_progress,
    admin_kpis,
    approved_cash_net,
    driver_cash_advance_total,
    driver_today_logged,
    manager_kpis,
    open_escalations,
)
from backend.app.db.queries.trips import get_active_trip_for_driver
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
                    driver_cash_advance_total(conn, trip_code)
                    + approved_cash_net(conn, trip_code)
                )
                if trip_code
                else 0.0,
            }
        else:
            return JSONResponse(
                status_code=403, content={"error": "forbidden", "code": "FORBIDDEN"}
            )

    return _ok(_jsonable(data))


@router.get("/dashboard/trends", response_model=Data[dict])
def api_dashboard_trends(request: Request):
    """30-day spend-by-type + leakage trend for the Super Admin (audit P-3)."""
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT created_at::date AS day, exp_type,
                      COALESCE(SUM(amount), 0) AS total
                 FROM expenses
                WHERE created_at >= CURRENT_DATE - INTERVAL '29 days'
                GROUP BY 1, 2
                ORDER BY 1"""
        )
        by_day = [
            {
                "day": r["day"].isoformat(),
                "exp_type": r["exp_type"],
                "total": float(r["total"]),
            }
            for r in cur.fetchall()
        ]
        cur.execute(
            """SELECT created_at::date AS day, COALESCE(SUM(amount), 0) AS total
                 FROM expenses
                WHERE manager_status = 'REJECTED'
                  AND exp_type <> 'SETTLEMENT_TRANSFER'
                  AND created_at >= CURRENT_DATE - INTERVAL '29 days'
                GROUP BY 1
                ORDER BY 1"""
        )
        leakage_by_day = [
            {"day": r["day"].isoformat(), "total": float(r["total"])}
            for r in cur.fetchall()
        ]

    totals: dict = {}
    for row in by_day:
        totals[row["exp_type"]] = totals.get(row["exp_type"], 0.0) + row["total"]
    return _ok(
        {
            "window_days": 30,
            "by_day": by_day,
            "leakage_by_day": leakage_by_day,
            "leakage_total": round(sum(r["total"] for r in leakage_by_day), 2),
            "totals_by_type": {k: round(v, 2) for k, v in sorted(totals.items())},
        }
    )
