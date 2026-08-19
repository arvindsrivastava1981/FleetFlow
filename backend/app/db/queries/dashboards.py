"""Query helpers for the role-based dashboards (`/admin`, `/manager`, `/driver`).

Pure SQL aggregations over `trips` / `expenses` / `vehicles`. These back the
Super Admin, Trip Manager, and Driver dashboard pages in `api/dashboards.py`.

Conventions (APP_MINDMAP.md):
- `%s` placeholders only; rows are plain `RealDict` dicts.
- Callers use `db/connection.get_db()` which commits on clean exit.

Cash-in-hand / float math (matches the settlement signs in `views.py`):
- Every approved non-GOODS expense reduces the driver's cash (paid from advance).
- An approved `GOODS_SALE` increases cash in hand (driver collects at delivery).
- Net balance per trip = advance + SUM(approved sales) - SUM(approved other).
"""
from __future__ import annotations


# ---------------------------------------------------------------------------#
# Admin (Fleet Owner) KPIs
# ---------------------------------------------------------------------------#
def admin_kpis(conn) -> dict:
    """Return top-line Super Admin KPIs:
    - active_trips / active_vehicles / active_drivers (fleet currently on the road)
    - mtd_spend_by_type (Diesel/DEF/Toll/Repairs/Challans for the month)
    - leakage_prevented (value of REJECTED claims, an estimate of money recovered)
    - outstanding_float (advance less approved net spend across open trips)
    """
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM trips WHERE status = 'ACTIVE'")
    active_trips = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM vehicles WHERE is_active = TRUE")
    active_vehicles = cur.fetchone()["c"]

    cur.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role = 'driver' AND is_active = TRUE"
    )
    active_drivers = cur.fetchone()["c"]

    cur.execute(
        """SELECT exp_type, COALESCE(SUM(amount), 0) AS total
             FROM expenses
            WHERE manager_status <> 'REJECTED'
              AND created_at >= date_trunc('month', CURRENT_DATE)
            GROUP BY exp_type"""
    )
    mtd_spend = {row["exp_type"]: row["total"] for row in cur.fetchall()}

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS saved "
        "FROM expenses WHERE manager_status = 'REJECTED'"
    )
    leakage_prevented = cur.fetchone()["saved"]

    cur.execute(
        """SELECT t.trip_code, t.vehicle_no, t.driver_name, t.advance_amount,
                  COALESCE(SUM(
                      CASE WHEN e.manager_status = 'APPROVED' THEN
                          (CASE WHEN e.exp_type = 'GOODS_SALE'
                                THEN COALESCE(e.approved_amount, e.amount)
                                ELSE -COALESCE(e.approved_amount, e.amount) END)
                      ELSE 0 END
                  ), 0) AS approved_net
             FROM trips t
             LEFT JOIN expenses e ON e.trip_code = t.trip_code
            WHERE t.status IN ('ACTIVE', 'COMPLETED')
            GROUP BY t.trip_code, t.vehicle_no, t.driver_name, t.advance_amount
            ORDER BY t.id"""
    )
    float_rows = cur.fetchall()
    outstanding_float = sum(
        (row["advance_amount"] or 0) + (row["approved_net"] or 0)
        for row in float_rows
    )

    return {
        "active_trips": active_trips,
        "active_vehicles": active_vehicles,
        "active_drivers": active_drivers,
        "mtd_spend_by_type": mtd_spend,
        "mtd_spend_total": sum(mtd_spend.values()),
        "leakage_prevented": leakage_prevented,
        "outstanding_float": outstanding_float,
        "float_by_trip": float_rows,
        "trips_in_float": len(float_rows),
    }


# ---------------------------------------------------------------------------#
# Manager (Trip / Fleet Manager) KPIs
# ---------------------------------------------------------------------------#
def manager_kpis(conn, manager_id: int | None = None) -> dict:
    """Operational shift KPIs for the Trip Manager dashboard.

    When *manager_id* is given, every aggregate is scoped to the trips that
    manager created (created_by = manager_id).
    """
    cur = conn.cursor()
    scope_sql = " AND created_by = %s" if manager_id else ""
    scope_params = (manager_id,) if manager_id else ()

    cur.execute(
        f"SELECT COUNT(*) AS c FROM trips WHERE status = 'ACTIVE'{scope_sql}",
        scope_params,
    )
    active_dispatched = cur.fetchone()["c"]

    cur.execute(
        f"""SELECT COUNT(*) AS c FROM expenses e
            WHERE (e.is_flagged = TRUE OR e.manager_status = 'PENDING')
              AND EXISTS (SELECT 1 FROM trips t
                           WHERE t.trip_code = e.trip_code{scope_sql})""",
        scope_params,
    )
    pending_escalations = cur.fetchone()["c"]

    cur.execute(
        f"SELECT COALESCE(SUM(advance_amount), 0) AS total "
        f"FROM trips WHERE created_at >= CURRENT_DATE{scope_sql}",
        scope_params,
    )
    advances_today = cur.fetchone()["total"]

    cur.execute(
        f"SELECT COUNT(*) AS c FROM trips WHERE status = 'COMPLETED'{scope_sql}",
        scope_params,
    )
    awaiting_settlement = cur.fetchone()["c"]

    return {
        "active_dispatched": active_dispatched,
        "pending_escalations": pending_escalations,
        "advances_today": advances_today,
        "awaiting_settlement": awaiting_settlement,
    }


def open_escalations(conn, limit: int = 20, manager_id: int | None = None) -> list[dict]:
    """Flagged / pending expenses needing a manager decision, newest first.

    When *manager_id* is given, only expenses on trips that manager created
    are returned.
    """
    cur = conn.cursor()
    scope_sql = " AND EXISTS (SELECT 1 FROM trips t WHERE t.trip_code = e.trip_code AND t.created_by = %s)" if manager_id else ""
    params = [manager_id, limit] if manager_id else [limit]
    cur.execute(
        f"""SELECT e.id, e.trip_code, e.exp_type, e.amount, e.liters, e.rate,
                  e.odometer, e.station_name, e.is_flagged, e.flag_reason,
                  e.manager_status, e.created_at
             FROM expenses e
            WHERE (e.is_flagged = TRUE OR e.manager_status = 'PENDING'){scope_sql}
            ORDER BY e.id DESC LIMIT %s""",
        params,
    )
    return cur.fetchall()


def open_escalations_detail(
    conn, limit: int = 50, manager_id: int | None = None
) -> list[dict]:
    """Flagged / pending expenses joined with their trip's driver + vehicle.

    Used by the Manager WhatsApp escalation view so each escalation message can
    label who logged it and on which vehicle. When *manager_id* is given, only
    expenses on trips that manager created are returned; omit to see everything
    (used for super_admin).
    """
    cur = conn.cursor()
    scope_sql = (
        " AND EXISTS (SELECT 1 FROM trips t WHERE t.trip_code = e.trip_code AND t.created_by = %s)"
        if manager_id
        else ""
    )
    params: list[object] = [limit]
    if manager_id:
        params.insert(0, manager_id)
    cur.execute(
        f"""SELECT e.id, e.trip_code, e.exp_type, e.amount, e.liters, e.rate,
                  e.odometer, e.station_name, e.is_flagged, e.flag_reason,
                  e.manager_status, e.created_at,
                  t.driver_name, t.vehicle_no, t.advance_amount, t.driver_batta_amount
             FROM expenses e
             LEFT JOIN trips t ON t.trip_code = e.trip_code
            WHERE (e.is_flagged = TRUE OR e.manager_status = 'PENDING'){scope_sql}
            ORDER BY e.id DESC LIMIT %s""",
        params,
    )
    return cur.fetchall()


def active_trip_progress(conn, manager_id: int | None = None) -> list[dict]:
    """ACTIVE trips with driver, odometer, cumulative claims, and remaining float.

    When *manager_id* is given, only trips that manager created are shown.
    """
    cur = conn.cursor()
    scope_sql = " AND t.created_by = %s" if manager_id else ""
    scope_params = (manager_id,) if manager_id else ()
    cur.execute(
        f"""SELECT t.trip_code, t.vehicle_no, t.driver_name, t.start_odo,
                  t.current_odo, t.advance_amount, t.driver_batta_amount,
                  COALESCE(SUM(
                      CASE WHEN e.manager_status IN ('APPROVED','PENDING')
                           THEN COALESCE(e.approved_amount, e.amount) ELSE 0 END
                  ), 0) AS claimed,
                  COALESCE(SUM(
                      CASE WHEN e.manager_status = 'PENDING' THEN 1 ELSE 0 END
                  ), 0) AS pending_n,
                  COALESCE(SUM(
                      CASE WHEN e.manager_status = 'APPROVED' THEN
                          (CASE WHEN e.exp_type = 'GOODS_SALE'
                                THEN COALESCE(e.approved_amount, e.amount)
                                ELSE -COALESCE(e.approved_amount, e.amount) END)
                      ELSE 0 END
                  ), 0) AS approved_net
             FROM trips t
             LEFT JOIN expenses e ON e.trip_code = t.trip_code
            WHERE t.status = 'ACTIVE'{scope_sql}
            GROUP BY t.id, t.trip_code, t.vehicle_no, t.driver_name, t.start_odo,
                     t.current_odo, t.advance_amount, t.driver_batta_amount
            ORDER BY t.id""",
        scope_params,
    )
    rows = cur.fetchall()
    for r in rows:
        # Align with the settlement engine: net_balance = advance + goods −
        # (road expenses + driver batta). `approved_net` is goods − road, so the
        # resolved trip batta is credited here to match compute_settlement.
        batta = r.get("driver_batta_amount")
        r["remaining_advance"] = (
            (r["advance_amount"] or 0) + (r["approved_net"] or 0) - (batta or 0)
        )
    return rows


def settlement_ready_trips(conn, manager_id: int | None = None) -> list[dict]:
    """ACTIVE trips with no PENDING expenses (safe for 1-click settlement).

    When *manager_id* is given, only trips that manager created are returned.
    """
    cur = conn.cursor()
    scope_sql = " AND t.created_by = %s" if manager_id else ""
    scope_params = (manager_id,) if manager_id else ()
    cur.execute(
        f"""SELECT t.trip_code, t.vehicle_no, t.driver_name, t.advance_amount,
                  t.driver_batta_amount,
                  COALESCE(SUM(
                      CASE WHEN e.manager_status = 'APPROVED' THEN
                          (CASE WHEN e.exp_type = 'GOODS_SALE'
                                THEN COALESCE(e.approved_amount, e.amount)
                                ELSE -COALESCE(e.approved_amount, e.amount) END)
                      ELSE 0 END
                  ), 0) AS approved_net
             FROM trips t
             LEFT JOIN expenses e ON e.trip_code = t.trip_code
            WHERE t.status = 'ACTIVE'{scope_sql}
            GROUP BY t.id, t.trip_code, t.vehicle_no, t.driver_name, t.advance_amount,
                     t.driver_batta_amount
           HAVING COALESCE(SUM(CASE WHEN e.manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) = 0
            ORDER BY t.id""",
        scope_params,
    )
    rows = cur.fetchall()
    for r in rows:
        batta = r.get("driver_batta_amount")
        r["returnable"] = (
            (r["advance_amount"] or 0)
            + (r["approved_net"] or 0)
            - (batta or 0)
        )
    return rows


# ---------------------------------------------------------------------------#
# Admin widgets (heatmap + leaderboard)
# ---------------------------------------------------------------------------#
def anomaly_heatmap(conn, limit: int = 8) -> list[dict]:
    """High-frequency flagged expense sources (station/pump hotspots)."""
    cur = conn.cursor()
    cur.execute(
        """SELECT COALESCE(NULLIF(e.station_name, ''), 'Unknown') AS station,
                  e.exp_type, COUNT(*) AS flagged_count,
                  COALESCE(SUM(e.amount), 0) AS flagged_amount
             FROM expenses e
            WHERE e.is_flagged = TRUE
            GROUP BY e.station_name, e.exp_type
            ORDER BY flagged_count DESC LIMIT %s""",
        (limit,),
    )
    return cur.fetchall()


def efficiency_leaderboard(conn, limit: int = 10) -> list[dict]:
    """Per-vehicle km/L performance vs. the target baseline (4.0 km/L).

    km/L = (highest odometer logged - trip start) / total approved fuel liters.
    Only vehicles with at least one approved FUEL entry are ranked.
    """
    cur = conn.cursor()
    cur.execute(
        """WITH dist AS (
                 SELECT t.vehicle_no, t.id AS trip_id,
                        t.start_odo,
                        GREATEST(t.current_odo,
                                 COALESCE(MAX(e.odometer), t.start_odo)) AS max_odo
                   FROM trips t
                   LEFT JOIN expenses e ON e.trip_code = t.trip_code
                  GROUP BY t.vehicle_no, t.id, t.start_odo, t.current_odo
             ),
             fuel AS (
                 SELECT trip_code, COALESCE(SUM(liters), 0) AS liters
                   FROM expenses
                  WHERE exp_type = 'FUEL' AND manager_status = 'APPROVED'
                  GROUP BY trip_code
             )
             SELECT d.vehicle_no,
                    SUM(d.max_odo - d.start_odo) AS distance_km,
                    COALESCE(SUM(f.liters), 0) AS liters,
                    MAX(v.expected_km_per_liter) AS target_kml
               FROM dist d
               LEFT JOIN fuel f ON f.trip_code =
                                 (SELECT trip_code FROM trips WHERE id = d.trip_id)
               LEFT JOIN vehicles v ON v.vehicle_number = d.vehicle_no
              GROUP BY d.vehicle_no
             HAVING COALESCE(SUM(f.liters), 0) > 0
             ORDER BY (SUM(d.max_odo - d.start_odo) / NULLIF(COALESCE(SUM(f.liters), 0), 0)) DESC
             LIMIT %s""",
        (limit,),
    )
    rows = cur.fetchall()
    for r in rows:
        denominator = r["liters"] or 0
        r["kml"] = (r["distance_km"] / denominator) if denominator else 0.0
    return rows


# ---------------------------------------------------------------------------#
# Driver KPIs
# ---------------------------------------------------------------------------#
def driver_today_logged(conn, trip_code: str) -> float:
    """Sum of approved expense amounts logged today on the given trip."""
    cur = conn.cursor()
    cur.execute(
        """SELECT COALESCE(SUM(amount), 0) AS total FROM expenses
            WHERE trip_code = %s AND manager_status = 'APPROVED'
              AND created_at >= CURRENT_DATE""",
        (trip_code,),
    )
    return cur.fetchone()["total"]


def approved_cash_net(conn, trip_code: str) -> float:
    """Net cash impact of all approved expenses (sales increase, others decrease)."""
    cur = conn.cursor()
    cur.execute(
        """SELECT COALESCE(SUM(
                   CASE WHEN exp_type = 'GOODS_SALE'
                        THEN COALESCE(approved_amount, amount)
                        ELSE -COALESCE(approved_amount, amount) END
               ), 0) AS net FROM expenses
            WHERE trip_code = %s AND manager_status = 'APPROVED'""",
        (trip_code,),
    )
    return cur.fetchone()["net"]