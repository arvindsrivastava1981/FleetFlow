"""Fleet analytics aggregates (feature F-4).

Super Admin sees platform-wide numbers; a Trip Manager sees only their own
fleet's aggregates (scoped via `users.fleet_id` -> `trips.fleet_id` /
`vehicles.fleet_id`).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import _identity, _ok
from backend.app.core.security import require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.users import get_user_fleet_id

router = APIRouter(prefix="/api/v1")


@router.get("/analytics/overview")
def api_analytics_overview(request: Request):
    """Cost-per-vehicle, driver-wise leakage, 6-month spend (audit F-4).

    Fleet-scoped for `trip_manager` (own fleet), platform-wide for `super_admin`.
    """
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard

    user = _identity(request)
    with get_db() as conn:
        cur = conn.cursor()

        fleet_id: int | None = None
        if user.get("role") == "trip_manager":
            fleet_id = get_user_fleet_id(conn, user.get("user_id"))
        # Tenant filter appended to each aggregate so a manager never sees
        # another fleet's spend/leakage; super_admin keeps the global view.
        fleet_where = "AND t.fleet_id = %s" if fleet_id is not None else ""
        fleet_args = [fleet_id] if fleet_id is not None else []
        # Outer vehicle filter (super_admin sees all fleets' vehicles).
        vehicle_where = "AND v.fleet_id = %s" if fleet_id is not None else ""

        # Cost per km per vehicle: spend from the ledger, km from trip odometers.
        cur.execute(
            f"""SELECT v.vehicle_number,
                      COALESCE(sp.spend, 0) AS spend,
                      COALESCE(km.km, 0) AS km
                 FROM vehicles v
                 LEFT JOIN (
                      SELECT t.vehicle_no AS vn, SUM(e.amount) AS spend
                        FROM expenses e
                        JOIN trips t ON t.trip_code = e.trip_code
                       WHERE 1=1 {fleet_where}
                       GROUP BY t.vehicle_no
                 ) sp ON sp.vn = v.vehicle_number
                 LEFT JOIN (
                      SELECT vehicle_no AS vn2,
                             SUM(GREATEST(current_odo - start_odo, 0)) AS km
                        FROM trips
                       WHERE 1=1 {fleet_where}
                       GROUP BY vehicle_no
                 ) km ON km.vn2 = v.vehicle_number
                WHERE COALESCE(sp.spend, 0) > 0
                  {vehicle_where}
                ORDER BY sp.spend DESC
                LIMIT 10""",
            # Two subquery filters + the outer vehicle filter = 3 params.
            (*fleet_args, *fleet_args, *fleet_args),
        )
        cost_per_km = []
        for r in cur.fetchall():
            spend, km = float(r["spend"]), float(r["km"])
            cost_per_km.append(
                {
                    "vehicle_number": r["vehicle_number"],
                    "spend": round(spend, 2),
                    "km": round(km, 1),
                    "cost_per_km": round(spend / km, 2) if km > 0 else None,
                }
            )

        # Driver-wise leakage prevented (rejected claims), attributed via the
        # trip's driver — expenses rows carry no creator column of their own.
        cur.execute(
            f"""SELECT u.full_name AS driver_name,
                      COALESCE(SUM(e.amount), 0) AS total
                 FROM expenses e
                 JOIN trips t ON t.trip_code = e.trip_code
                 JOIN users u ON u.id = t.driver_user_id
                WHERE e.manager_status = 'REJECTED'
                  AND e.exp_type <> 'SETTLEMENT_TRANSFER'
                  {fleet_where}
                GROUP BY u.full_name
                ORDER BY total DESC
                LIMIT 10""",
            fleet_args,
        )
        driver_leakage = [
            {
                "driver_name": r["driver_name"],
                "total": round(float(r["total"]), 2),
            }
            for r in cur.fetchall()
        ]

        # Monthly spend for the last 6 months.
        cur.execute(
            f"""SELECT to_char(e.created_at, 'YYYY-MM') AS month,
                      COALESCE(SUM(e.amount), 0) AS total
                 FROM expenses e
                 JOIN trips t ON t.trip_code = e.trip_code
                WHERE e.created_at >= date_trunc('month', CURRENT_DATE)
                                      - INTERVAL '5 months'
                  {fleet_where}
                GROUP BY 1
                ORDER BY 1""",
            fleet_args,
        )
        monthly_spend = [
            {"month": r["month"], "total": round(float(r["total"]), 2)}
            for r in cur.fetchall()
        ]

    payload: dict[str, Any] = {
        "cost_per_km": cost_per_km,
        "driver_leakage": driver_leakage,
        "monthly_spend": monthly_spend,
    }
    return _ok(payload)
