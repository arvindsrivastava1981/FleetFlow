"""Query helpers for the `trips` table.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and return plain dict rows / booleans. None of them commit — the caller's
`get_db()` contextmanager commits on clean exit.
"""
from __future__ import annotations


def active_trip_exists(conn, fleet_id: int | None = None) -> bool:
    """True when an ACTIVE trip exists, scoped to *fleet_id* when provided.

    Multi-tenant isolation: the "one active trip" invariant applies per fleet,
    not globally across all tenants.
    """
    cur = conn.cursor()
    if fleet_id is not None:
        cur.execute(
            "SELECT 1 FROM trips WHERE status = 'ACTIVE' AND fleet_id = %s LIMIT 1",
            (fleet_id,),
        )
    else:
        cur.execute("SELECT 1 FROM trips WHERE status = 'ACTIVE' LIMIT 1")
    return cur.fetchone() is not None


def get_all_trips(conn) -> list[dict]:
    """All trips, active first then newest-created first."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM trips ORDER BY CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END, id DESC"
    )
    return cur.fetchall()


def get_trip_by_code(conn, trip_code: str) -> dict | None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM trips WHERE trip_code = %s", (trip_code,))
    return cur.fetchone()


def get_latest_active_trip(conn) -> dict | None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM trips WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
    return cur.fetchone()


def get_latest_active_trip_for_user(conn, user_id: int | None, role: str) -> dict | None:
    """Latest ACTIVE trip visible to *user_id* based on their *role*.

    Mirrors `get_trips_for_user` scoping so a trip_manager only resolves their
    own active trip and a driver only their assigned one.
    """
    cur = conn.cursor()
    if role == "trip_manager":
        cur.execute(
            "SELECT * FROM trips WHERE created_by = %s AND status = 'ACTIVE' "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
    elif role == "driver":
        cur.execute(
            "SELECT * FROM trips WHERE driver_user_id = %s AND status = 'ACTIVE' "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
    else:  # super_admin
        cur.execute("SELECT * FROM trips WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
    return cur.fetchone()


def get_trip_stats_by_code(conn) -> dict[str, dict]:
    """Per-trip expense aggregates keyed by trip_code, for the trips/ listings."""
    cur = conn.cursor()
    cur.execute(
        """SELECT trip_code, COUNT(*) AS expense_count,
                  COALESCE(SUM(amount), 0) AS total_claimed,
                  COALESCE(SUM(CASE WHEN manager_status = 'APPROVED' OR (NOT is_flagged AND manager_status != 'REJECTED') THEN amount ELSE 0 END), 0) AS total_approved,
                  COALESCE(SUM(CASE WHEN is_flagged THEN amount ELSE 0 END), 0) AS flagged_amount,
                  COALESCE(SUM(CASE WHEN manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
           FROM expenses GROUP BY trip_code"""
    )
    return {row["trip_code"]: row for row in cur.fetchall()}


def trip_status(conn, trip_code: str) -> str | None:
    """Return the status of a trip, or None if the trip doesn't exist."""
    cur = conn.cursor()
    cur.execute("SELECT status FROM trips WHERE trip_code = %s", (trip_code,))
    row = cur.fetchone()
    return row["status"] if row else None


def insert_trip(
    conn,
    fleet_id: int | None,
    trip_code: str,
    vehicle_no: str,
    driver_name: str,
    driver_phone: str,
    advance_amount: float,
    start_odo: float,
    created_by: int | None = None,
    driver_user_id: int | None = None,
    vehicle_id: int | None = None,
) -> None:
    """Insert a new ACTIVE trip. Caller checks `active_trip_exists` first.
    *fleet_id* is REQUIRED (schema: trips.fleet_id NOT NULL) and binds the trip
    to its owning tenant. *created_by* is the trip_manager who started the trip;
    *driver_user_id* links the trip to a driver user so drivers can see their
    own trips. *vehicle_id* links the trip to the vehicle selected from the
    dropdown.
    """
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO trips
               (fleet_id, trip_code, vehicle_id, vehicle_no, driver_name, driver_phone,
                advance_amount, start_odo, current_odo, status,
                created_by, driver_user_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s)""",
        (fleet_id, trip_code, vehicle_id, vehicle_no, driver_name, driver_phone,
         advance_amount, start_odo, start_odo,
         created_by, driver_user_id),
    )


def get_trips_for_user(conn, user_id: int, role: str) -> list[dict]:
    """Return trips visible to *user_id* based on their *role*.

    - super_admin: all trips
    - trip_manager: trips they created (created_by = user_id)
    - driver: trips assigned to them (driver_user_id = user_id)
    """
    cur = conn.cursor()
    if role == "super_admin":
        cur.execute(
            "SELECT * FROM trips ORDER BY "
            "CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END, id DESC"
        )
        return cur.fetchall()
    if role == "trip_manager":
        cur.execute(
            "SELECT * FROM trips WHERE created_by = %s ORDER BY "
            "CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END, id DESC",
            (user_id,),
        )
        return cur.fetchall()
    # driver
    cur.execute(
        "SELECT * FROM trips WHERE driver_user_id = %s ORDER BY "
        "CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END, id DESC",
        (user_id,),
    )
    return cur.fetchall()


def get_active_trip_for_driver(conn, user_id: int) -> dict | None:
    """Latest ACTIVE trip assigned to *user_id* (driver view)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM trips WHERE driver_user_id = %s AND status = 'ACTIVE' "
        "ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return cur.fetchone()


def get_active_trip_for_manager(conn, user_id: int) -> dict | None:
    """Latest ACTIVE trip created by *user_id* (trip_manager view)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM trips WHERE created_by = %s AND status = 'ACTIVE' "
        "ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return cur.fetchone()


def settle_trip(conn, trip_code: str) -> None:
    """Mark a trip SETTLED (only called after confirming no PENDING expenses)."""
    cur = conn.cursor()
    cur.execute(
        """UPDATE trips
            SET status = 'SETTLED', end_odo = current_odo,
                completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                settled_at = CURRENT_TIMESTAMP
          WHERE trip_code = %s AND status = 'ACTIVE'""",
        (trip_code,),
    )


def pending_expense_count(conn, trip_code: str) -> int:
    """Number of still-PENDING expenses for a trip (blocks settlement)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS pending_count FROM expenses "
        "WHERE trip_code = %s AND manager_status = 'PENDING'",
        (trip_code,),
    )
    return cur.fetchone()["pending_count"]