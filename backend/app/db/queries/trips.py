"""Query helpers for the `trips` table.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and return plain dict rows / booleans. None of them commit — the caller's
`get_db()` contextmanager commits on clean exit.
"""
from __future__ import annotations

import re
from backend.app.services.audit.cash import compute_settlement


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


def next_trip_code(conn, vehicle_no: str) -> str:
    """Auto-generate the next trip_code as `{last4-of-plate}-{next-number}`.

    The prefix is the final 4 digits of the vehicle number (e.g. `UP32MA1234`
    -> `1234`). The suffix is the highest existing trip number for that prefix
    plus one, so codes increment per vehicle and never collide across distinct
    plates that happen to share the same last-4 digits (trip_code is UNIQUE).

    Tie-break: the highest numeric suffix wins (WHEN `1234-1` and `1234-01`
    coexist, the next code is `1234-2`).
    """
    last4 = (vehicle_no or "").strip()[-4:]
    if not last4.isdigit() or len(last4) != 4:
        last4 = "0000"

    cur = conn.cursor()
    cur.execute(
        """SELECT trip_code FROM trips
           WHERE trip_code ~ ('^' || %s || '-(\\d+)$')
           ORDER BY (regexp_replace(trip_code, '^' || %s || '-(\\d+)$', '\\1'))::int DESC
           LIMIT 1""",
        (re.escape(last4), re.escape(last4)),
    )
    row = cur.fetchone()
    last_number = int(row["trip_code"].split("-")[-1]) if row else 0
    return f"{last4}-{last_number + 1}"


def insert_trip(
    conn,
    fleet_id: int | None,
    vehicle_no: str,
    driver_name: str,
    driver_phone: str,
    advance_amount: float,
    start_odo: float,
    created_by: int | None = None,
    driver_user_id: int | None = None,
    vehicle_id: int | None = None,
    driver_batta_amount: float | None = None,
) -> str:
    """Insert a new ACTIVE trip. Caller checks `active_trip_exists` first.

    The `trip_code` is auto-generated (via `next_trip_code`) as
    `{last4-of-plate}-{next-number}`; the generated code is returned so callers
    can redirect/report the exact code created. *fleet_id* is REQUIRED (schema:
    trips.fleet_id NOT NULL) and binds the trip to its owning tenant.
    *created_by* is the trip_manager who started the trip; *driver_user_id*
    links the trip to a driver user so drivers can see their own trips.
    *vehicle_id* links the trip to the vehicle selected from the dropdown.
    *driver_batta_amount* is the resolved batta snapshotted from the driver's
    profile at creation (None -> DB default ₹2,500).
    """
    trip_code = next_trip_code(conn, vehicle_no)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO trips
               (fleet_id, trip_code, vehicle_id, vehicle_no, driver_name, driver_phone,
                advance_amount, start_odo, current_odo, status,
                created_by, driver_user_id, driver_batta_amount)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s, %s)""",
        (fleet_id, trip_code, vehicle_id, vehicle_no, driver_name, driver_phone,
         advance_amount, start_odo, start_odo,
         created_by, driver_user_id, driver_batta_amount),
    )
    return trip_code


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
    """Mark a trip SETTLED and persist the settlement verification fingerprint.

    Only called after confirming no PENDING expenses. Uses the single-source
    netting engine to compute the deterministic verification hash + resolved
    batta, and writes them in the same transaction that flips status so a
    historical print's voucher code is stable and verifiable.
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM trips WHERE trip_code = %s AND status = 'ACTIVE'", (trip_code,))
    trip = cur.fetchone()
    if trip is None:
        return

    cur.execute(
        "SELECT * FROM expenses WHERE trip_code = %s AND manager_status = 'APPROVED'",
        (trip_code,),
    )
    approved_expenses = cur.fetchall()

    settlement = compute_settlement(trip, approved_expenses)

    cur.execute(
        """UPDATE trips
            SET status = 'SETTLED', end_odo = current_odo,
                completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                settled_at = CURRENT_TIMESTAMP,
                verification_hash = %s,
                driver_batta_amount = %s
          WHERE trip_code = %s AND status = 'ACTIVE'""",
        (settlement.verification_hash, settlement.driver_batta, trip_code),
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