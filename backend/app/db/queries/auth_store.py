"""Durable backing store for auth sessions + login throttling (audit R-1).

The in-process dicts in ``core/security.py`` stay the hot path; these helpers
mirror state into Postgres so sessions survive restarts and are shared across
instances, and brute-force counters are not reset by a deploy. Only the
SHA-256 **hash** of each session token is ever stored, never the raw token.

Every caller wraps these in a best-effort try/except — persistence must never
turn a working in-memory flow into a hard outage.
"""
from __future__ import annotations

from typing import Any


def insert_auth_session(
    conn,
    token_hash: str,
    user_id: int,
    username: str,
    role: str,
    issued_at,
    expires_at,
) -> None:
    """Upsert one session row (*issued_at* / *expires_at* are aware datetimes)."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO auth_sessions
               (token_hash, user_id, username, role, issued_at, expires_at)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (token_hash) DO UPDATE
                SET user_id = EXCLUDED.user_id,
                    username = EXCLUDED.username,
                    role = EXCLUDED.role,
                    issued_at = EXCLUDED.issued_at,
                    expires_at = EXCLUDED.expires_at""",
        (token_hash, user_id, username, role, issued_at, expires_at),
    )


def fetch_auth_session(conn, token_hash: str) -> dict[str, Any] | None:
    """Return an unexpired session row for *token_hash*, else None."""
    cur = conn.cursor()
    cur.execute(
        """SELECT user_id, username, role, issued_at
             FROM auth_sessions
            WHERE token_hash = %s AND expires_at > NOW()""",
        (token_hash,),
    )
    return cur.fetchone()


def delete_auth_session(conn, token_hash: str) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_sessions WHERE token_hash = %s", (token_hash,))


def delete_auth_sessions_for_user(conn, user_id: int) -> int:
    """Revoke every stored session for *user_id* (fleet-wide B-1 revocation)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_sessions WHERE user_id = %s", (user_id,))
    return cur.rowcount


def delete_expired_auth_sessions(conn) -> int:
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_sessions WHERE expires_at < NOW()")
    return cur.rowcount


def get_login_throttle(conn, ip: str) -> tuple[int, float] | None:
    """Return ``(failures, locked_until_epoch | 0.0)`` for *ip*, else None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT failures, locked_until FROM login_throttle WHERE ip = %s", (ip,)
    )
    row = cur.fetchone()
    if row is None:
        return None
    locked_epoch = row["locked_until"].timestamp() if row["locked_until"] else 0.0
    return int(row["failures"]), float(locked_epoch)


def upsert_login_throttle(conn, ip: str, failures: int, locked_until) -> None:
    """Mirror the throttle state (*locked_until*: aware datetime or None)."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO login_throttle (ip, failures, locked_until, updated_at)
           VALUES (%s, %s, %s, NOW())
           ON CONFLICT (ip) DO UPDATE
                SET failures = EXCLUDED.failures,
                    locked_until = EXCLUDED.locked_until,
                    updated_at = NOW()""",
        (ip, failures, locked_until),
    )


def clear_login_throttle(conn, ip: str) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM login_throttle WHERE ip = %s", (ip,))
