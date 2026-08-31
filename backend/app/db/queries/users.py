from __future__ import annotations

from backend.app.services.audit.cash import DEFAULT_DRIVER_BATTA as DEFAULT_BATTA_RATE

BATTA_TYPES = ("FIXED_TRIP", "PER_KM", "DAILY", "NONE")
DEFAULT_BATTA_TYPE = "FIXED_TRIP"


def _normalise_batta(batta_type, default_batta_rate):
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


def get_driver_batta_profile(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, full_name, phone, batta_type, default_batta_rate "
        "FROM users WHERE id=%s",
        (user_id,),
    )
    return cur.fetchone()


def get_user_by_email(conn, email):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE lower(email) = %s", (email.strip().lower(),))
    return cur.fetchone()


def get_user_by_phone(conn, phone):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE phone = %s", (phone,))
    return cur.fetchone()


def get_user_by_id(conn, user_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cur.fetchone()


def get_user_by_provider(conn, provider, provider_sub):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE auth_provider = %s AND provider_sub = %s", (provider, provider_sub))
    return cur.fetchone()


def get_all_users(conn, role_filter=None, limit=None, offset=0):
    cur = conn.cursor()
    page_sql = " LIMIT %s OFFSET %s" if limit is not None else ""
    if role_filter:
        cur.execute("SELECT * FROM users WHERE role = %s ORDER BY id" + page_sql,
                    [role_filter, *([limit, offset] if limit is not None else [])])
    else:
        cur.execute("SELECT * FROM users ORDER BY id" + page_sql,
                    [limit, offset] if limit is not None else [])
    return cur.fetchall()


def get_drivers_for_user(conn, role="super_admin", user_id=None, limit=None, offset=0):
    page_sql = " LIMIT %s OFFSET %s" if limit is not None else ""
    if role == "super_admin":
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE role = 'driver' ORDER BY id DESC" + page_sql,
                    [limit, offset] if limit is not None else [])
        return cur.fetchall()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE role = 'driver' AND created_by = %s ORDER BY id DESC" + page_sql,
        [user_id, *([limit, offset] if limit is not None else [])] if user_id else
        [0, *([limit, offset] if limit is not None else [])],
    )
    return cur.fetchall()


def get_users_by_roles(conn, roles):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE role = ANY(%s) ORDER BY id", (list(roles),))
    return cur.fetchall()


def create_user(conn, email, password_hash, full_name, role, phone=None,
                created_by=None, fleet_id=None, batta_type=None, default_batta_rate=None):
    bt, rate = _normalise_batta(batta_type, default_batta_rate)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users (email, password_hash, full_name, role, phone, is_active,
                created_by, fleet_id, batta_type, default_batta_rate)
            VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s)
            RETURNING id""",
        (email, password_hash, full_name, role, phone, created_by, fleet_id, bt, rate),
    )
    return cur.fetchone()["id"]


def create_or_link_social_user(conn, provider, provider_sub, email, full_name, default_role="trip_manager"):
    # Defense-in-depth: social sign-up is untrusted self-signup — it is ALWAYS a
    # trip_manager. super_admin comes only from the manual seed script and
    # drivers are only created by a trip_manager, so any passed default_role
    # (even a misconfigured env override) is overridden here.
    _safe_role = "trip_manager"
    existing = get_user_by_provider(conn, provider, provider_sub)
    if existing is not None:
        return existing, False
    linked = get_user_by_email(conn, email)
    if linked is not None:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET auth_provider=%s, provider_sub=%s, full_name=COALESCE(NULLIF(%s,''), full_name) WHERE id=%s",
            (provider, provider_sub, full_name, linked["id"]),
        )
        return get_user_by_id(conn, linked["id"]), False
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users (email, password_hash, full_name, role, is_active, auth_provider, provider_sub)
            VALUES (%s, %s, %s, %s, TRUE, %s, %s)
            RETURNING id""",
        (email, f"!social:{provider}:{provider_sub}", full_name, _safe_role, provider, provider_sub),
    )
    return get_user_by_id(conn, cur.fetchone()["id"]), True


def update_user(conn, user_id, full_name, role, phone=None, email=None, is_active=None,
                password_hash=None, fleet_id=None, batta_type=None, default_batta_rate=None):
    cur = conn.cursor()
    fields, values = [], []
    if full_name is not None:
        fields.append("full_name=%s")
        values.append(full_name)
    if role is not None:
        fields.append("role=%s")
        values.append(role)
    if phone is not None:
        fields.append("phone=%s")
        values.append(phone)
    if email is not None:
        fields.append("email=%s")
        values.append(email)
    if is_active is not None:
        fields.append("is_active=%s")
        values.append(is_active)
    if password_hash is not None:
        fields.append("password_hash=%s")
        values.append(password_hash)
    if fleet_id is not None:
        fields.append("fleet_id=%s")
        values.append(fleet_id)
    if batta_type is not None:
        bt, rate = _normalise_batta(batta_type, default_batta_rate)
        fields.append("batta_type=%s")
        values.append(bt)
        fields.append("default_batta_rate=%s")
        values.append(rate)
    if not fields:
        return False
    values.append(user_id)
    cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", values)
    return cur.rowcount > 0


def get_user_fleet_id(conn, user_id):
    cur = conn.cursor()
    cur.execute("SELECT fleet_id FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    return row["fleet_id"] if row else None


def get_user_by_verify_token(conn, token):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email_verify_token=%s AND email_verify_expires_at>NOW()", (token,))
    return cur.fetchone()


def register_user(conn, email, password_hash, full_name, phone, email_verify_token, email_verify_expires_at):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users (email, password_hash, full_name, role, phone,
                is_active, email_verified, email_verify_token, email_verify_expires_at, auth_provider)
            VALUES (%s, %s, %s, 'trip_manager', %s, TRUE, FALSE, %s, %s, 'local')
            RETURNING *""",
        (email, password_hash, full_name, phone, email_verify_token, email_verify_expires_at),
    )
    return cur.fetchone()


def verify_email(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET email_verified=TRUE, email_verify_token=NULL, email_verify_expires_at=NULL WHERE id=%s",
        (user_id,),
    )
    return cur.rowcount > 0


def deactivate_user(conn, user_id):
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active=FALSE WHERE id=%s", (user_id,))
    return cur.rowcount > 0


def reactivate_user(conn, user_id):
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active=TRUE WHERE id=%s", (user_id,))
    return cur.rowcount > 0
