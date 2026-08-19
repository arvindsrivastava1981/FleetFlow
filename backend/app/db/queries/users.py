"""Query helpers for the `users` table.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and return plain dict rows / booleans. None of them commit — the caller's
`get_db()` contextmanager commits on clean exit.
"""
from __future__ import annotations

# Valid driver remuneration modes (aligned with the users.batta_type CHECK;
# DEFAULT_* are the fallbacks when a driver does not opt in to a specific profile).
BATTA_TYPES: tuple[str, ...] = ("FIXED_TRIP", "PER_KM", "DAILY", "NONE")
DEFAULT_BATTA_TYPE = "FIXED_TRIP"
DEFAULT_BATTA_RATE = 2500.00


def _normalise_batta(
    batta_type: str | None,
    default_batta_rate: float | str | None,
) -> tuple[str, float]:
    """Return a validated (batta_type, default_batta_rate) pair.

    Falls back to the schema defaults (FIXED_TRIP / ₹2,500.00) when a value is
    missing or outside the allowed whitelist, so DB-level CHECK/DEFAULT invariants
    are preserved from the application layer too.
    """
    bt = (batta_type or "").strip().upper() or DEFAULT_BATTA_TYPE
    if bt not in BATTA_TYPES:
        bt = DEFAULT_BATTA_TYPE
    if bt == "NONE":
        return bt, 0.0
    rate = default_batta_rate
    if rate is None or rate == "":
        return bt, DEFAULT_BATTA_RATE
    try:
        return bt, round(float(rate), 2)
    except (TypeError, ValueError):
        return bt, DEFAULT_BATTA_RATE


def get_user_by_username(conn, username: str) -> dict | None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    return cur.fetchone()


def get_user_by_id(conn, user_id: int) -> dict | None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cur.fetchone()


def get_all_users(conn, role_filter: str | None = None) -> list[dict]:
    cur = conn.cursor()
    if role_filter:
        cur.execute("SELECT * FROM users WHERE role = %s ORDER BY id", (role_filter,))
    else:
        cur.execute("SELECT * FROM users ORDER BY id")
    return cur.fetchall()


def get_users_by_roles(conn, roles: tuple[str, ...]) -> list[dict]:
    """Return users whose role is in *roles* (for driver dropdowns)."""
    if not roles:
        return []
    placeholders = ",".join(["%s"] * len(roles))
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM users WHERE role IN ({placeholders}) AND is_active = TRUE "
        f"ORDER BY id",
        roles,
    )
    return cur.fetchall()


def get_driver_batta_profile(conn, user_id: int | None) -> dict | None:
    """Return the batta-relevant subset of a driver user's profile (or None).

    Lightweight lookup used at trip creation to resolve the batta to snapshot.
    """
    if not user_id:
        return None
    cur = conn.cursor()
    cur.execute(
        "SELECT id, batta_type, default_batta_rate "
        "FROM users WHERE id = %s AND role = 'driver'",
        (user_id,),
    )
    return cur.fetchone()


def create_user(
    conn,
    username: str,
    password_hash: str,
    full_name: str,
    role: str,
    phone: str | None = None,
    email: str | None = None,
    created_by: int | None = None,
    fleet_id: int | None = None,
    batta_type: str | None = None,
    default_batta_rate: float | str | None = None,
) -> int:
    """Insert a new user and return the new ID.

    *fleet_id* binds a trip_manager/driver to the fleet they belong to
    (the fleet they create vehicles under). For drivers, *batta_type* and
    *default_batta_rate* set the remuneration profile (defaults to FIXED_TRIP
    / ₹2,500.00); NONE disables batta for that driver.
    """
    bt, rate = _normalise_batta(batta_type, default_batta_rate)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users
               (username, password_hash, full_name, role, phone, email, is_active,
                created_by, fleet_id, batta_type, default_batta_rate)
           VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s)
           RETURNING id""",
        (username, password_hash, full_name, role, phone, email,
         created_by, fleet_id, bt, rate),
    )
    return cur.fetchone()["id"]


def update_user(
    conn,
    user_id: int,
    full_name: str,
    role: str,
    phone: str | None = None,
    email: str | None = None,
    is_active: bool | None = None,
    password_hash: str | None = None,
    fleet_id: int | None = None,
    batta_type: str | None = None,
    default_batta_rate: float | str | None = None,
) -> bool:
    """Update a user. Returns True if a row was updated.

    *batta_type* / *default_batta_rate* update the driver remuneration profile
    when provided (None leaves the existing values untouched). Pass an empty
    string sentinel to explicitly reset `default_batta_rate` back to the default.
    """
    cur = conn.cursor()
    fields = []
    values = []
    if full_name is not None:
        fields.append("full_name = %s")
        values.append(full_name)
    if role is not None:
        fields.append("role = %s")
        values.append(role)
    if phone is not None:
        fields.append("phone = %s")
        values.append(phone)
    if email is not None:
        fields.append("email = %s")
        values.append(email)
    if is_active is not None:
        fields.append("is_active = %s")
        values.append(is_active)
    if password_hash is not None:
        fields.append("password_hash = %s")
        values.append(password_hash)
    if fleet_id is not None:
        fields.append("fleet_id = %s")
        values.append(fleet_id)
    if batta_type is not None:
        bt, rate = _normalise_batta(batta_type, default_batta_rate)
        fields.append("batta_type = %s")
        values.append(bt)
        fields.append("default_batta_rate = %s")
        values.append(rate)
    if not fields:
        return False
    values.append(user_id)
    cur.execute(
        f"UPDATE users SET {', '.join(fields)} WHERE id = %s",
        values,
    )
    return cur.rowcount > 0


def get_user_fleet_id(conn, user_id: int) -> int | None:
    """Return the fleet_id bound to a user (their owning fleet), if any."""
    cur = conn.cursor()
    cur.execute("SELECT fleet_id FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    return row["fleet_id"] if row else None


def deactivate_user(conn, user_id: int) -> bool:
    """Soft-delete: set is_active = FALSE."""
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (user_id,))
    return cur.rowcount > 0


def reactivate_user(conn, user_id: int) -> bool:
    """Set is_active = TRUE."""
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active = TRUE WHERE id = %s", (user_id,))
    return cur.rowcount > 0
