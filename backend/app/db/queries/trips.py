"""Query helpers for the `trips` table.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and return plain dict rows / booleans. None of them commit — the caller's
`get_db()` contextmanager commits on clean exit.
"""
from __future__ import annotations


def active_trip_exists(conn) -> bool:
    """True when any trip is currently ACTIVE (only one active trip allowed)."""
    cur = conn.cursor()
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


def get_trip_stats_by_code(conn) -> dict[str, dict]:
    """Per-trip expense aggregates keyed by trip_code, for the trips/admin listings."""
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
    trip_code: str,
    vehicle_no: str,
    driver_name: str,
    driver_phone: str,
    advance_amount: float,
    start_odo: float,
) -> None:
    """Insert a new ACTIVE trip. Caller checks `active_trip_exists` first."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO trips
               (trip_code, vehicle_no, driver_name, driver_phone,
                advance_amount, start_odo, current_odo, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')""",
        (trip_code, vehicle_no, driver_name, driver_phone,
         advance_amount, start_odo, start_odo),
    )


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