"""Super-admin analytics aggregates (feature F-4)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import _ok
from backend.app.core.security import require_json_role
from backend.app.db.connection import get_db

router = APIRouter(prefix="/api/v1")


@router.get("/analytics/overview")
def api_analytics_overview(request: Request):
    """Cost-per-vehicle, driver-wise leakage, 6-month spend (audit F-4)."""
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard

    with get_db() as conn:
        cur = conn.cursor()

        # Cost per km per vehicle: spend from the ledger, km from trip odometers.
        cur.execute(
            """SELECT v.vehicle_number,
                      COALESCE(sp.spend, 0) AS spend,
                      COALESCE(km.km, 0) AS km
                 FROM vehicles v
                 LEFT JOIN (
                      SELECT t.vehicle_no AS vn, SUM(e.amount) AS spend
                        FROM expenses e
                        JOIN trips t ON t.trip_code = e.trip_code
                       GROUP BY t.vehicle_no
                 ) sp ON sp.vn = v.vehicle_number
                 LEFT JOIN (
                      SELECT vehicle_no AS vn2,
                             SUM(GREATEST(current_odo - start_odo, 0)) AS km
                        FROM trips GROUP BY vehicle_no
                 ) km ON km.vn2 = v.vehicle_number
                WHERE COALESCE(sp.spend, 0) > 0
                ORDER BY sp.spend DESC
                LIMIT 10"""
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

        # Driver-wise leakage prevented (rejected claims).
        cur.execute(
            """SELECT u.full_name AS driver_name,
                      COALESCE(SUM(e.amount), 0) AS total
                 FROM expenses e
                 JOIN users u ON u.id = e.created_by
                WHERE e.manager_status = 'REJECTED'
                  AND e.exp_type <> 'SETTLEMENT_TRANSFER'
                GROUP BY u.full_name
                ORDER BY total DESC
                LIMIT 10"""
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
            """SELECT to_char(created_at, 'YYYY-MM') AS month,
                      COALESCE(SUM(amount), 0) AS total
                 FROM expenses
                WHERE created_at >= date_trunc('month', CURRENT_DATE)
                                      - INTERVAL '5 months'
                GROUP BY 1
                ORDER BY 1"""
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
