"""Named SQL query helpers.

One module per core table, exposing focused functions that take a
`psycopg2` connection/cursor and return plain rows. Routers never write SQL
inline here — they call these functions (wrapped further by `models/`).

- trips.py        : active-trip guards, insert, settle, pending count
- expenses.py     : insert expense (with trip-id resolution), update status
- fleets.py       : (Phase B / future multi-fleet features)
- fuel_benchmarks.py : per-state price index CRUD
- toll_corridors.py  : Phase B FASTag corridors
"""
from __future__ import annotations

from backend.app.db.queries.expenses import action_expense_status, insert_expense
from backend.app.db.queries.trips import (
    active_trip_exists,
    insert_trip,
    pending_expense_count,
    settle_trip,
    trip_status,
)

__all__ = [
    "action_expense_status",
    "active_trip_exists",
    "insert_expense",
    "insert_trip",
    "pending_expense_count",
    "settle_trip",
    "trip_status",
]