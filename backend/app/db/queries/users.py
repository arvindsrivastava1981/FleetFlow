from __future__ import annotations

# Valid driver remuneration modes (aligned with the users.batta_type CHECK;
# DEFAULT_* are the fallbacks when a driver does not opt in to a specific profile).
from backend.app.services.audit.cash import DEFAULT_DRIVER_BATTA as DEFAULT_BATTA_RATE

BATTA_TYPES: tuple[str, ...] = ("FIXED_TRIP", "PER_KM", "DAILY", "NONE")
DEFAULT_BATTA_TYPE = "FIXED_TRIP"


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


def get_user_by_phone(conn, phone: str) -> dict | None:
    """Return the single user bound to a normalized WhatsApp *phone* (or None).

    Used by the single WhatsApp webhook (backend/app/api/v1/whatsapp.py) to
    resolve a sender's number to a ``users`` row and thereby their role, so one
    bot number can route drivers' receipt messages to the expense-intake flow
    and managers' quick-reply payloads to the escalation-approval flow. Pass a
    normalized ``+91XXXXXXXXXX`` value (see ``services/whatsapp.normalise_number``).
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE phone = %s", (phone,))
    return cur.fetchone()


def get_user_by_id(conn, user_id: int) -> dict | None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cur.fetchone()


def get_all_users(
    conn,
    role_filter: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """All users, bounded when *limit* is given (audit R-7 pagination)."""
    cur = conn.cursor()
    page_sql = " LIMIT %s OFFSET %s" if limit is not None else ""
    if role_filter:
        cur.execute(
            "SELECT * FROM users WHERE role = %s ORDER BY id" + page_sql,
            [role_filter, *([limit, offset] if limit is not None else [])],
        )
    else:
        cur.execute(
            "SELECT * FROM users ORDER BY id" + page_sql,
            [limit, offset] if limit is not None else [],
        )
    return cur.fetchall()


def get_drivers_for_user(
    conn,
    role: str = "super_admin",
    user_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Return drivers visible to the caller, newest first.

    super_admin sees every driver; a trip_manager sees ONLY the drivers they
    created (users.created_by) — mirroring the vehicles ownership clause — so
    one manager's drivers are never listed to another manager.
    Rows are bounded when *limit* is given (audit R-7 pagination).
    """
    cur = conn.cursor()
    page_sql = " LIMIT %s OFFSET %s" if limit is not None else ""
    if role == "super_admin":
        cur.execute(
            "SELECT * FROM users WHERE role = 'driver' ORDER BY id" + page_sql,
            [limit, offset] if limit is not None else [],
        )
    else:
        cur.execute(
            "SELECT * FROM users WHERE role = 'driver' AND created_by = %s "
            "ORDER BY id" + page_sql,
            [user_id, *([limit, offset] if limit is not None else [])],
        )
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
        "SELECT id, phone, batta_type, default_batta_rate "
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
