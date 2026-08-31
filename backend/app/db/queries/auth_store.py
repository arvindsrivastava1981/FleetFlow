"""Durable backing store for auth sessions + login throttling (audit R-1)."""
from __future__ import annotations


def insert_auth_session(conn, token_hash, user_id, role, issued_at, expires_at):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO auth_sessions (token_hash, user_id, role, issued_at, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (token_hash) DO UPDATE
                SET user_id=EXCLUDED.user_id, role=EXCLUDED.role,
                    issued_at=EXCLUDED.issued_at, expires_at=EXCLUDED.expires_at""",
        (token_hash, user_id, role, issued_at, expires_at),
    )


def fetch_auth_session(conn, token_hash):
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, role, issued_at, expires_at FROM auth_sessions WHERE token_hash=%s AND expires_at>NOW()",
        (token_hash,),
    )
    return cur.fetchone()


def delete_auth_session(conn, token_hash):
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_sessions WHERE token_hash=%s", (token_hash,))


def delete_auth_sessions_for_user(conn, user_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_sessions WHERE user_id=%s", (user_id,))
    return cur.rowcount


def delete_expired_auth_sessions(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_sessions WHERE expires_at<NOW()")
    return cur.rowcount


def get_login_throttle(conn, ip):
    cur = conn.cursor()
    cur.execute("SELECT failures, locked_until FROM login_throttle WHERE ip=%s", (ip,))
    row = cur.fetchone()
    if row is None:
        return None
    locked_epoch = row["locked_until"].timestamp() if row["locked_until"] else 0.0
    return int(row["failures"]), float(locked_epoch)


def upsert_login_throttle(conn, ip, failures, locked_until):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO login_throttle (ip, failures, locked_until, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (ip) DO UPDATE SET failures=EXCLUDED.failures, locked_until=EXCLUDED.locked_until, updated_at=NOW()""",
        (ip, failures, locked_until),
    )


def clear_login_throttle(conn, ip):
    cur = conn.cursor()
    cur.execute("DELETE FROM login_throttle WHERE ip=%s", (ip,))
