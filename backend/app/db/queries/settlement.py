"""Query helpers for the `trips` table related to settlements.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and return plain dict rows / booleans. None of them commit — the caller's
`get_db()` contextmanager commits on clean exit.
"""
from __future__ import annotations


def get_settled_trips(conn, role: str = "super_admin", user_id: int | None = None) -> list[dict]:
    """Return trips with status SETTLED visible to the caller.

    trip_manager only sees trips they created; driver only their assigned ones;
    super_admin sees all.
    """
    cur = conn.cursor()
    if role == "trip_manager":
        cur.execute(
            "SELECT * FROM trips WHERE status = 'SETTLED' AND created_by = %s "
            "ORDER BY settled_at DESC",
            (user_id,),
        )
    elif role == "driver":
        cur.execute(
            "SELECT * FROM trips WHERE status = 'SETTLED' AND driver_user_id = %s "
            "ORDER BY settled_at DESC",
            (user_id,),
        )
    else:
        cur.execute(
            "SELECT * FROM trips WHERE status = 'SETTLED' ORDER BY settled_at DESC"
        )
    return cur.fetchall()


def get_trip_settlement_data(conn, trip_code: str) -> dict | None:
    """Return full settlement data for a specific trip code."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM trips WHERE trip_code = %s AND status = 'SETTLED'", (trip_code,))
    return cur.fetchone()