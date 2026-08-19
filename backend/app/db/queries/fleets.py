from __future__ import annotations

from datetime import datetime

import psycopg2.extras


# --- Plans ---------------------------------------------------------------

def get_all_plans(conn) -> list[dict]:
    """Return the active plan catalogue, TRIAL-first then by price."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM subscription_plans WHERE is_active = TRUE "
        "ORDER BY CASE code WHEN 'TRIAL' THEN 0 ELSE 1 END, price"
    )
    return cur.fetchall()


def get_plan_by_code(conn, code: str) -> dict | None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM subscription_plans WHERE code = %s", (code,))
    return cur.fetchone()


# --- Fleets ---------------------------------------------------------------

def get_all_fleets(conn, fleet_id: int | None = None) -> list[dict]:
    """Fleets newest-first, with plan name and vehicle count.

    Pass *fleet_id* to restrict the result to a single fleet (used for a
    trip_manager's "own fleet" view on the Fleets page).
    """
    cur = conn.cursor()
    where = "WHERE f.id = %s" if fleet_id is not None else ""
    params: list = [fleet_id] if fleet_id is not None else []
    cur.execute(
        f"""
        SELECT f.*, sp.name AS plan_name, sp.code AS plan_code,
               (SELECT COUNT(*) FROM vehicles v
                 WHERE v.fleet_id = f.id AND v.is_active = TRUE) AS vehicle_count
          FROM fleets f
          LEFT JOIN subscription_plans sp ON sp.id = f.plan_id
         {where}
         ORDER BY f.id DESC
        """,
        params,
    )
    return cur.fetchall()


def get_fleet_by_id(conn, id: int) -> dict | None:
    """Return a single fleet row (no join) by ID."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM fleets WHERE id = %s", (id,))
    return cur.fetchone()


def get_fleet_email_context(conn, fleet_id: int) -> dict | None:
    """Return the data a Trip Manager onboarding email needs for a fleet.

    Enriches the fleet row with:
      * ``plan_name``  — subscription plan display name (via `subscription_plans`),
      * ``driver_limit`` — count of **active** driver users in the fleet.
    ``default_batta_rate`` is *not* a fleet attribute; the email context assumes
    the product default and falls back only when present on the row.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.*, sp.name AS plan_name,
               (SELECT COUNT(*) FROM users u
                 WHERE u.fleet_id = f.id AND u.role = 'driver'
                   AND u.is_active = TRUE) AS driver_limit
          FROM fleets f
          LEFT JOIN subscription_plans sp ON sp.id = f.plan_id
         WHERE f.id = %s
        """,
        (fleet_id,),
    )
    return cur.fetchone()


def get_fleet_detail(conn, id: int) -> dict | None:
    """Single fleet with plan_name and vehicle_count (for the detail page)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.*, sp.name AS plan_name, sp.code AS plan_code,
               (SELECT COUNT(*) FROM vehicles v
                 WHERE v.fleet_id = f.id AND v.is_active = TRUE) AS vehicle_count,
               (SELECT COUNT(*) FROM users u
                 WHERE u.fleet_id = f.id AND u.role = 'trip_manager'
                   AND u.is_active = TRUE) AS manager_count
          FROM fleets f
          LEFT JOIN subscription_plans sp ON sp.id = f.plan_id
         WHERE f.id = %s
        """,
        (id,),
    )
    return cur.fetchone()


def get_default_fleet(conn) -> dict | None:
    """Return the first active fleet, used to bind runtime vehicle creations."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM fleets WHERE is_active = TRUE ORDER BY id ASC LIMIT 1"
    )
    return cur.fetchone()


def fleet_phone_exists(conn, phone: str, exclude_id: int | None = None) -> bool:
    """True when a fleet with this phone already exists (unique phone)."""
    cur = conn.cursor()
    if exclude_id is not None:
        cur.execute(
            "SELECT 1 FROM fleets WHERE phone = %s AND id <> %s",
            (phone, exclude_id),
        )
    else:
        cur.execute("SELECT 1 FROM fleets WHERE phone = %s", (phone,))
    return cur.fetchone() is not None


def insert_fleet(
    conn,
    owner_name: str,
    phone: str,
    email: str | None = None,
    subscription_plan: str = "MONTHLY",
) -> int:
    """Create a new fleet starting its 15-day trial on the TRIAL plan.

    Returns the new fleet id. The 15-day trial clock starts now.
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO fleets
            (owner_name, phone, email, subscription_plan,
             plan_id, subscription_status,
             trial_started_at, trial_ends_at, vehicle_limit)
        VALUES
            (%s, %s, %s, %s,
             (SELECT id FROM subscription_plans WHERE code = 'TRIAL'),
             'TRIAL', CURRENT_TIMESTAMP,
             CURRENT_TIMESTAMP + INTERVAL '15 days', 1)
        RETURNING id
        """,
        (owner_name, phone, email, subscription_plan),
    )
    return cur.fetchone()["id"]


def update_fleet(
    conn,
    id: int,
    owner_name: str,
    phone: str,
    email: str | None = None,
) -> bool:
    """Update a fleet's contact details. Returns True if a row was updated."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE fleets SET owner_name = %s, phone = %s, email = %s WHERE id = %s",
        (owner_name, phone, email, id),
    )
    return cur.rowcount > 0


def deactivate_fleet(conn, id: int) -> bool:
    """Soft-delete a fleet (is_active = FALSE). Returns True if updated."""
    cur = conn.cursor()
    cur.execute("UPDATE fleets SET is_active = FALSE WHERE id = %s", (id,))
    return cur.rowcount > 0


def reactivate_fleet(conn, id: int) -> bool:
    """Set is_active = TRUE for a fleet. Returns True if updated."""
    cur = conn.cursor()
    cur.execute("UPDATE fleets SET is_active = TRUE WHERE id = %s", (id,))
    return cur.rowcount > 0


# --- Subscription state ------------------------------------------------

def count_active_vehicles(conn, fleet_id: int) -> int:
    """Number of active vehicles registered under a fleet."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS c FROM vehicles WHERE fleet_id = %s AND is_active = TRUE",
        (fleet_id,),
    )
    return cur.fetchone()["c"]


def is_trial_active(conn, fleet_id: int) -> bool:
    """True when the fleet is in TRIAL and its 15-day window hasn't lapsed."""
    cur = conn.cursor()
    cur.execute(
        "SELECT subscription_status, trial_ends_at FROM fleets WHERE id = %s",
        (fleet_id,),
    )
    row = cur.fetchone()
    if not row:
        return False
    if row["subscription_status"] != "TRIAL":
        return False
    return row["trial_ends_at"] is not None and row["trial_ends_at"] >= datetime.now()


def get_fleet_entitlement(conn, fleet_id: int) -> dict | None:
    """Return the fleet's effective vehicle limit + status for the gate.

    Handles trial expiry: a TRIAL fleet whose window has lapsed is reported
    as PAST_DUE so callers can block vehicle creation and route to billing.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.subscription_status, f.trial_ends_at, f.vehicle_limit,
               f.razorpay_subscription_id, sp.code AS plan_code
          FROM fleets f
          LEFT JOIN subscription_plans sp ON sp.id = f.plan_id
         WHERE f.id = %s
        """,
        (fleet_id,),
    )
    fleet = cur.fetchone()
    if not fleet:
        return None
    # A TRIAL fleet whose window lapsed behaves like PAST_DUE.
    if fleet["subscription_status"] == "TRIAL":
        if fleet["trial_ends_at"] is None or fleet["trial_ends_at"] < datetime.now():
            fleet["subscription_status"] = "PAST_DUE"
    return fleet


def start_trial_subscription(conn, fleet_id: int) -> None:
    """Start (or restart) the free 15-day trial for a fleet.

    Since the trial is ₹0 there is no Razorpay payment — the manager picks the
    Trial Pack on the upgrade page and the trial clock (re)starts immediately
    so they can continue registering vehicles. Clears billing references so a
    previous subscription doesn't leak into the trial window.
    """
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE fleets
           SET plan_id = (SELECT id FROM subscription_plans WHERE code = 'TRIAL'),
               subscription_plan = 'TRIAL',
               subscription_status = 'TRIAL',
               vehicle_limit = (SELECT vehicle_limit FROM subscription_plans WHERE code = 'TRIAL'),
               trial_started_at = CURRENT_TIMESTAMP,
               trial_ends_at = CURRENT_TIMESTAMP + INTERVAL '15 days',
               next_billing_date = NULL,
               razorpay_subscription_id = NULL,
               razorpay_customer_id = NULL
         WHERE id = %s
        """,
        (fleet_id,),
    )


def set_plan_subscription(
    conn,
    fleet_id: int,
    plan_code: str,
    razorpay_subscription_id: str | None = None,
    razorpay_customer_id: str | None = None,
) -> None:
    """Activate a subscription plan for a fleet (used by billing success)."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE fleets
           SET plan_id = (SELECT id FROM subscription_plans WHERE code = %s),
               subscription_status = 'ACTIVE',
               vehicle_limit = (SELECT vehicle_limit FROM subscription_plans WHERE code = %s),
               next_billing_date = CURRENT_DATE + INTERVAL '1 month',
               razorpay_subscription_id = COALESCE(%s, razorpay_subscription_id),
               razorpay_customer_id = COALESCE(%s, razorpay_customer_id)
         WHERE id = %s
        """,
        (plan_code, plan_code, razorpay_subscription_id, razorpay_customer_id, fleet_id),
    )


def set_yearly_subscription(conn, fleet_id: int) -> None:
    """Apply the yearly plan (25% off) and set the 12-month billing date."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE fleets
           SET plan_id = (SELECT id FROM subscription_plans WHERE code = 'YEARLY'),
               subscription_status = 'ACTIVE',
               vehicle_limit = (SELECT vehicle_limit FROM subscription_plans WHERE code = 'YEARLY'),
               next_billing_date = CURRENT_DATE + INTERVAL '12 months'
         WHERE id = %s
        """,
        (fleet_id,),
    )



def bump_vehicle_limit(conn, fleet_id: int) -> None:
    """Raise the fleet vehicle cap by 1 (single-vehicle subscription purchase)."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE fleets SET vehicle_limit = vehicle_limit + 1 WHERE id = %s",
        (fleet_id,),
    )


def mark_subscription_past_due(conn, fleet_id: int) -> None:
    """Flip a fleet to PAST_DUE (webhook: payment failed / subscription cancelled)."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE fleets SET subscription_status = 'PAST_DUE' WHERE id = %s",
        (fleet_id,),
    )


def extend_billing_date(conn, fleet_id: int, months: int = 1) -> None:
    """Extend next_billing_date by *months* (webhook: recurring charge succeeded)."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE fleets SET next_billing_date = COALESCE(next_billing_date, CURRENT_DATE) "
        "+ INTERVAL '1 month' * %s WHERE id = %s",
        (months, fleet_id),
    )


# --- Billing audit ledger ------------------------------------------------

def log_fleet_billing_event(
    conn,
    fleet_id: int,
    event_type: str,
    plan_code: str | None = None,
    payload: dict | None = None,
    razorpay_ref: str | None = None,
    amount: float | None = None,
    created_by: int | None = None,
) -> None:
    """Append a row to the fleet_billing_events audit ledger.

    Every entitlement mutation (plan change, extra slot purchase, trial start,
    payment) writes a row so limit changes are explainable and reversible (G6/G10).
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO fleet_billing_events
            (fleet_id, event_type, plan_code, payload, razorpay_ref, amount, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (fleet_id, event_type, plan_code,
         psycopg2.extras.Json(payload or {}), razorpay_ref, amount, created_by),
    )


def get_fleet_billing_events(conn, fleet_id: int, limit: int = 50) -> list[dict]:
    """Return the recent billing/entitlement events for a fleet, newest-first."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, event_type, plan_code, payload, razorpay_ref, amount,
               created_by, created_at
          FROM fleet_billing_events
         WHERE fleet_id = %s
         ORDER BY created_at DESC
         LIMIT %s
        """,
        (fleet_id, limit),
    )
    return cur.fetchall()

