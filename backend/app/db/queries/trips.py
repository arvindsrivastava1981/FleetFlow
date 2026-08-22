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
    """All trips, active first then newest-created first, with driver info."""
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
             FROM trips t
             LEFT JOIN users u ON u.id = t.driver_user_id
            ORDER BY CASE WHEN t.status = 'ACTIVE' THEN 0 ELSE 1 END, t.id DESC"""
    )
    return cur.fetchall()


def get_trip_by_code(conn, trip_code: str) -> dict | None:
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
             FROM trips t
             LEFT JOIN users u ON u.id = t.driver_user_id
            WHERE t.trip_code = %s""",
        (trip_code,),
    )
    return cur.fetchone()


def get_latest_active_trip(conn) -> dict | None:
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
             FROM trips t
             LEFT JOIN users u ON u.id = t.driver_user_id
            WHERE t.status = 'ACTIVE' ORDER BY t.id DESC LIMIT 1"""
    )
    return cur.fetchone()


def get_trip_stats_by_code(conn) -> dict[str, dict]:
    """Per-trip expense aggregates keyed by trip_code, for the trips/ listings."""
    cur = conn.cursor()
    cur.execute(
        """SELECT trip_code,
                  COUNT(*) AS expense_count,
                  COALESCE(SUM(amount), 0) AS total_claimed,
                  COALESCE(SUM(CASE WHEN manager_status = 'APPROVED' OR (NOT is_flagged AND manager_status != 'REJECTED') THEN amount ELSE 0 END), 0) AS total_approved,
                  COALESCE(SUM(CASE WHEN is_flagged THEN amount ELSE 0 END), 0) AS flagged_amount,
                  COALESCE(SUM(CASE WHEN manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
           FROM expenses
          GROUP BY trip_code"""
    )
    return {row["trip_code"]: row for row in cur.fetchall()}


def trip_status(conn, trip_code: str) -> str | None:
    """Return the status of a trip, or None if the trip doesn't exist."""
    cur = conn.cursor()
    cur.execute("SELECT status FROM trips WHERE trip_code = %s", (trip_code,))
    row = cur.fetchone()
    return row["status"] if row else None


def update_trip_odometer(conn, trip_code: str, odometer: float) -> None:
    """Monotonic odo roll-up on the trip row (never steps the odometer back).

    Mirrors the rule in the legacy prototype: only ever raises `current_odo`,
    so a lower reading logged later is ignored. Called from the expense-creation
    flow after a wallet/FUEL expense is accepted.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE trips SET current_odo = GREATEST(current_odo, %s) "
        "WHERE trip_code = %s",
        (odometer, trip_code),
    )


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
    start_odo: float,
    created_by: int | None = None,
    driver_user_id: int | None = None,
    vehicle_id: int | None = None,
    state_code: str | None = None,
) -> str:
    """Insert a new ACTIVE trip. Caller checks `active_trip_exists` first.

    The `trip_code` is auto-generated (via `next_trip_code`) as
    `{last4-of-plate}-{next-number}`; the generated code is returned so callers
    can redirect/report the exact code created. *fleet_id* is REQUIRED (schema:
    trips.fleet_id NOT NULL) and binds the trip to its owning tenant.
    *created_by* is the trip_manager who started the trip; *driver_user_id*
    links the trip to a driver user so drivers can see their own trips.
    *vehicle_id* links the trip to the vehicle selected from the dropdown.
    *state_code* captures the operating state (derived from the vehicle plate)
    so the rules engine can pick a per-state fuel benchmark band.

    driver_name / driver_phone / advance / batta are NOT stored here: driver
    identity is derived via JOIN with users on driver_user_id, and cash advance
    + driver batta are posted as CASH_ADVANCE / DRIVER_SALARY expense rows by
    the route (single-source ledger), not duplicated on the trip row.
    """
    # Serialize trip-code generation per plate (audit B-4): two concurrent
    # creations for one vehicle previously raced `next_trip_code`'s SELECT-max
    # against this INSERT and died on the UNIQUE constraint (raw 500). The
    # transaction-scoped advisory lock auto-releases on commit/rollback.
    cur = conn.cursor()
    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (vehicle_no,))
    trip_code = next_trip_code(conn, vehicle_no)
    cur.execute(
        """INSERT INTO trips
               (fleet_id, trip_code, vehicle_id, vehicle_no,
                start_odo, current_odo, status,
                created_by, driver_user_id, state_code)
           VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s, %s)""",
        (fleet_id, trip_code, vehicle_id, vehicle_no,
         start_odo, start_odo,
         created_by, driver_user_id, state_code),
    )
    return trip_code


def get_trips_for_user(
    conn,
    user_id: int,
    role: str,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Return trips visible to *user_id* based on their *role*.

    - super_admin: all trips
    - trip_manager: trips they created (created_by = user_id)
    - driver: trips assigned to them (driver_user_id = user_id)

    Joins users to resolve driver_name / driver_phone from the users table
    (no longer denormalized on trips).
    """
    cur = conn.cursor()
    base = """
        SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
          FROM trips t
          LEFT JOIN users u ON u.id = t.driver_user_id
    """
    order = " ORDER BY CASE WHEN t.status = 'ACTIVE' THEN 0 ELSE 1 END, t.id DESC"
    page_sql = " LIMIT %s OFFSET %s" if limit is not None else ""  # audit R-7

    if role == "super_admin":
        cur.execute(base + order + page_sql,
                    [limit, offset] if limit is not None else [])
        return cur.fetchall()
    if role == "trip_manager":
        where = " WHERE t.created_by = %s"
        params: list = [user_id]
    # driver
    else:
        where = " WHERE t.driver_user_id = %s"
        params = [user_id]
    if limit is not None:
        params += [limit, offset]
    cur.execute(base + where + order + page_sql, params)
    return cur.fetchall()


def get_active_trip_for_driver(conn, user_id: int) -> dict | None:
    """Latest ACTIVE trip assigned to *user_id* (driver view), with driver info."""
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
             FROM trips t
             LEFT JOIN users u ON u.id = t.driver_user_id
            WHERE t.driver_user_id = %s AND t.status = 'ACTIVE'
            ORDER BY t.id DESC LIMIT 1""",
        (user_id,),
    )
    return cur.fetchone()


def get_active_trip_for_manager(conn, user_id: int) -> dict | None:
    """Latest ACTIVE trip created by *user_id* (trip_manager view)."""
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
             FROM trips t
             LEFT JOIN users u ON u.id = t.driver_user_id
            WHERE t.created_by = %s AND t.status = 'ACTIVE'
            ORDER BY t.id DESC LIMIT 1""",
        (user_id,),
    )
    return cur.fetchone()


def settle_trip(conn, trip_code: str, manager_id: int | None = None, end_odo: float | None = None) -> None:
    """Mark a trip SETTLED, persist the verification fingerprint + manager consent.

    Only called after confirming no PENDING expenses. Uses the single-source
    netting engine to compute the deterministic verification hash + resolved
    batta, and writes them in the same transaction that flips status so a
    historical print's voucher code is stable and verifiable.

    The manager's settlement is an implicit consent: the authenticated *manager_id*
    (the one performing the settle) is stamped onto ``manager_consent_by/_at``
    with a DB-authoritative timestamp, so the voucher's bilingual "Manager
    Acceptance" line is auditable. Accepts both ACTIVE and COMPLETED trips: a
    trip may be marked COMPLETED by the driver/field flow before the manager
    performs the final settlement, so the settle action must not be stripped for
    that intermediate state.

    *end_odo* must already have been validated (>= start_odo) upstream; if
    provided it overrides the auto-derived value from current_odo.
    """
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
             FROM trips t
             LEFT JOIN users u ON u.id = t.driver_user_id
            WHERE t.trip_code = %s AND t.status IN ('ACTIVE', 'COMPLETED')""",
        (trip_code,),
    )
    trip = cur.fetchone()
    if trip is None:
        return

    cur.execute(
        "SELECT * FROM expenses WHERE trip_code = %s AND manager_status = 'APPROVED'",
        (trip_code,),
    )
    approved_expenses = cur.fetchall()

    settlement = compute_settlement(trip, approved_expenses)

    # Use the caller-supplied end_odo when provided (already validated upstream),
    # else fall back to current_odo for backwards compatibility.
    closing_odo = end_odo if end_odo is not None else trip.get("current_odo")

    cur.execute(
        """UPDATE trips
            SET status = 'SETTLED', end_odo = %s,
                completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                settled_at = CURRENT_TIMESTAMP,
                verification_hash = %s,
                manager_consent_by = COALESCE(manager_consent_by, %s),
                manager_consent_at = COALESCE(manager_consent_at, CURRENT_TIMESTAMP)
          WHERE trip_code = %s AND status IN ('ACTIVE', 'COMPLETED')""",
        (closing_odo, settlement.verification_hash, manager_id, trip_code),
    )


def driver_consent(conn, trip_code: str, driver_id: int) -> bool:
    """Record a driver's explicit settlement consent (idempotent).

    Stamps the driver's identity + a DB-authoritative timestamp on their trip so
    the PDF's bilingual "Driver Acceptance" line lists a real acceptance. The
    first consent wins (``COALESCE``) — a driver cannot overwrite an earlier
    consent, keeping the trail tamper-evident. Returns True when a NEW consent
    was written, False when it was a no-op (already consented / trip unknown).
    """
    cur = conn.cursor()
    cur.execute(
        """UPDATE trips
            SET driver_consent_by = COALESCE(driver_consent_by, %s),
                driver_consent_at = COALESCE(driver_consent_at, CURRENT_TIMESTAMP)
          WHERE trip_code = %s AND driver_user_id = %s
            AND driver_consent_at IS NULL""",
        (driver_id, trip_code, driver_id),
    )
    return cur.rowcount > 0


def pending_expense_count(conn, trip_code: str) -> int:
    """Number of still-PENDING expenses for a trip (blocks settlement)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS pending_count FROM expenses "
        "WHERE trip_code = %s AND manager_status = 'PENDING'",
        (trip_code,),
    )
    return cur.fetchone()["pending_count"]
