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