"""Query helpers for the `users` table.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and return plain dict rows / booleans. None of them commit — the caller's
`get_db()` contextmanager commits on clean exit.
"""
from __future__ import annotations


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


def create_user(
    conn,
    username: str,
    password_hash: str,
    full_name: str,
    role: str,
    phone: str | None = None,
    email: str | None = None,
    created_by: int | None = None,
) -> int:
    """Insert a new user and return the new ID."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users
               (username, password_hash, full_name, role, phone, email, is_active, created_by)
           VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
           RETURNING id""",
        (username, password_hash, full_name, role, phone, email, created_by),
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
) -> bool:
    """Update a user. Returns True if a row was updated."""
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
    if not fields:
        return False
    values.append(user_id)
    cur.execute(
        f"UPDATE users SET {', '.join(fields)} WHERE id = %s",
        values,
    )
    return cur.rowcount > 0


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
