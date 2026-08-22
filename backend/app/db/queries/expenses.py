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
    state_code: str | None = None,
    raw_receipt_text: str | None = None,
) -> None:
    """Insert an expense row, resolving `trip_id` from the trips table first.

    *state_code* records the fueling state the driver picked for a fuel/DEF
    purchase (the state the band was evaluated against). It is omitted for
    non-fuel/auto-posted rows. *raw_receipt_text* carries the driver's
    free-text description (e.g. what a MISC/Kanta payment was for) verbatim.
    """
    cur = conn.cursor()
    cur.execute("SELECT id FROM trips WHERE trip_code = %s", (trip_code,))
    trip = cur.fetchone()
    trip_id = trip["id"] if trip else None
    cur.execute(
        """INSERT INTO expenses
               (trip_id, trip_code, exp_type, amount, liters, rate, odometer,
                is_flagged, flag_reason, manager_status, state_code,
                raw_receipt_text)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (trip_id, trip_code, exp_type, amount, liters, rate, odometer,
         is_flagged, flag_reason, manager_status, state_code,
         raw_receipt_text),
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
    """All expenses for a trip, newest first (for settlement computation).

    Returns **every** row including the auto-posted `CASH_ADVANCE` /
    `DRIVER_SALARY` provision legs — settlement math (`compute_settlement`)
    depends on them. Use `get_ledger_expenses_for_trip` for a user-facing
    display where provisions should be hidden.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM expenses WHERE trip_code = %s ORDER BY id DESC", (trip_code,)
    )
    return cur.fetchall()


def get_ledger_expenses_for_trip(conn, trip_code: str) -> list[dict]:
    """All expenses for a trip, newest first (for the ledger/table view).

    Returns **every** row including the auto-posted `CASH_ADVANCE` /
    `DRIVER_SALARY` provision legs so they are visible everywhere.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM expenses "
        "WHERE trip_code = %s "
        "ORDER BY id DESC",
        (trip_code,),
    )
    return cur.fetchall()


def open_settlement_request(conn, trip_code: str) -> dict | None:
    """Return the trip's live SETTLEMENT_TRANSFER row, if one exists.

    A "live" request is PENDING (awaiting manager action) or already APPROVED
    (acceptance recorded). Only REJECTED requests free the ledger for a fresh
    initiation, so at most one live closing entry can exist per trip.
    """
    cur = conn.cursor()
    cur.execute(
        """SELECT id, amount, manager_status
             FROM expenses
            WHERE trip_code = %s
              AND exp_type = 'SETTLEMENT_TRANSFER'
              AND manager_status IN ('PENDING', 'APPROVED')
            ORDER BY id DESC LIMIT 1""",
        (trip_code,),
    )
    return cur.fetchone()


def get_expense_by_id(conn, expense_id: int) -> dict | None:
    """Fetch one expense row (type/amount/actor) for action-side checks."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
    return cur.fetchone()
