"""Query helpers for the `expenses` table.

Fixing §2.7 from deep_agent_recommendation: every live expense now resolves and
persists `expenses.trip_id` at insert (previously always NULL at runtime), so
the FK + `idx_expenses_trip_id` actually mean something for cascades/deletes.
"""
from __future__ import annotations


def insert_expense(
    conn,
    trip_code: str,
    exp_type: str,
    amount: float,
    liters: float,
    rate: float,
    odometer: float,
    is_flagged: bool,
    flag_reason: str | None,
    manager_status: str,
) -> None:
    """Insert an expense row, resolving `trip_id` from the trips table first."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM trips WHERE trip_code = %s", (trip_code,))
    trip = cur.fetchone()
    trip_id = trip["id"] if trip else None
    cur.execute(
        """INSERT INTO expenses
               (trip_id, trip_code, exp_type, amount, liters, rate, odometer,
                is_flagged, flag_reason, manager_status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (trip_id, trip_code, exp_type, amount, liters, rate, odometer,
         is_flagged, flag_reason, manager_status),
    )


def action_expense_status(conn, expense_id: int, status: str) -> str:
    """Set an expense's manager_status and return its trip_code for redirect."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE expenses SET manager_status = %s WHERE id = %s",
        (status, expense_id),
    )
    cur.execute("SELECT trip_code FROM expenses WHERE id = %s", (expense_id,))
    row = cur.fetchone()
    return row["trip_code"] if row else ""


def get_expense_trip_code(conn, expense_id: int) -> str:
    """Return the trip_code an expense belongs to, without mutating it."""
    cur = conn.cursor()
    cur.execute("SELECT trip_code FROM expenses WHERE id = %s", (expense_id,))
    row = cur.fetchone()
    return row["trip_code"] if row else ""


def get_expenses_for_trip(conn, trip_code: str) -> list[dict]:
    """All expenses for a trip, newest first (for the ledger view)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM expenses WHERE trip_code = %s ORDER BY id DESC", (trip_code,)
    )
    return cur.fetchall()