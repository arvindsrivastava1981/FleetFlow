"""Super-admin error-log inspection queries (error_logs table).

The table itself is fed best-effort by the global error handlers in
``core/errors.py``. These helpers power the Super Admin “Error Logs” page:
a grouped summary (endpoint + type + message → count + last_seen), a
per-group delete, and a clear-all.
"""
from __future__ import annotations

from typing import Literal

GroupSort = Literal["count", "last_seen"]

# Grouping key: route identifier (falls back to raw path when the endpoint
# was not matched), error type, status, and the message itself. NULL-safe
# via COALESCE so probe traffic with NULL endpoints groups together.
_GROUP_SQL = """
    SELECT
        COALESCE(endpoint, path, '(unknown)') AS endpoint,
        error_type,
        status_code,
        COALESCE(message, '') AS message,
        COUNT(*) AS count,
        MAX(created_at) AS last_seen
    FROM error_logs
    GROUP BY 1, 2, 3, 4
"""

_SORTS = {
    "count": "count DESC, last_seen DESC",
    "last_seen": "last_seen DESC, count DESC",
}


def list_error_groups(
    conn, *, limit: int = 20, offset: int = 0, sort: GroupSort = "count"
) -> dict:
    """Grouped error summary with total group + total occurrence counts."""
    order = _SORTS.get(sort, _SORTS["count"])
    with conn.cursor() as cur:
        cur.execute(
            f"{_GROUP_SQL} ORDER BY {order} LIMIT %s OFFSET %s", (limit, offset)
        )
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.execute(f"SELECT COUNT(*), COALESCE(SUM(count), 0) FROM ({_GROUP_SQL}) g")
        total_groups, total_occurrences = cur.fetchone()
    groups = [dict(zip(cols, r)) for r in rows]
    return {
        "groups": groups,
        "total_groups": int(total_groups or 0),
        "total_occurrences": int(total_occurrences or 0),
    }


def delete_error_group(
    conn, *, endpoint: str, error_type: str, status_code: int, message: str
) -> int:
    """Delete every row in one group; returns rows removed (0 = not found)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM error_logs
            WHERE COALESCE(endpoint, path, '(unknown)') = %s
              AND error_type = %s
              AND status_code = %s
              AND COALESCE(message, '') = %s
            """,
            (endpoint, error_type, status_code, message),
        )
        deleted = cur.rowcount
    return int(deleted)


def list_error_rows(
    conn,
    *,
    limit: int = 20,
    offset: int = 0,
    endpoint: str | None = None,
    error_type: str | None = None,
    status_code: int | None = None,
    message: str | None = None,
) -> list[dict]:
    """Raw `error_logs` rows (every column), newest first.

    Optional filters narrow to one group (the same NULL-safe group key used by
    :func:`list_error_groups`); without filters this returns the full table.
    """
    where = ["1=1"]
    params: list = []
    if endpoint is not None:
        where.append("COALESCE(endpoint, path, '(unknown)') = %s")
        params.append(endpoint)
    if error_type is not None:
        where.append("error_type = %s")
        params.append(error_type)
    if status_code is not None:
        where.append("status_code = %s")
        params.append(status_code)
    if message is not None:
        where.append("COALESCE(message, '') = %s")
        params.append(message)
    sql = (
        "SELECT id, method, path, status_code, error_type, message, detail, "
        "traceback_text, endpoint, request_id, source, created_at "
        "FROM error_logs WHERE " + " AND ".join(where) +
        " ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s"
    )
    params += [limit, offset]
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def count_error_rows(
    conn,
    *,
    endpoint: str | None = None,
    error_type: str | None = None,
    status_code: int | None = None,
    message: str | None = None,
) -> int:
    """Total raw-row count matching the same optional group filters."""
    where = ["1=1"]
    params: list = []
    if endpoint is not None:
        where.append("COALESCE(endpoint, path, '(unknown)') = %s")
        params.append(endpoint)
    if error_type is not None:
        where.append("error_type = %s")
        params.append(error_type)
    if status_code is not None:
        where.append("status_code = %s")
        params.append(status_code)
    if message is not None:
        where.append("COALESCE(message, '') = %s")
        params.append(message)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM error_logs WHERE " + " AND ".join(where), params)
        return int(cur.fetchone()[0] or 0)


def clear_error_logs(conn) -> int:
    """Remove every error-log row; returns the number deleted."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM error_logs")
        deleted = cur.rowcount
    return int(deleted)