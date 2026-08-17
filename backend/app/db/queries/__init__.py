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
    get_active_trip_for_driver,
    get_active_trip_for_manager,
    get_all_trips,
    get_latest_active_trip,
    get_trip_by_code,
    get_trip_stats_by_code,
    get_trips_for_user,
    insert_trip,
    pending_expense_count,
    settle_trip,
    trip_status,
)
from backend.app.db.queries.users import (
    create_user,
    deactivate_user,
    get_all_users,
    get_user_by_id,
    get_user_by_username,
    get_users_by_roles,
    reactivate_user,
    update_user,
)

__all__ = [
    "action_expense_status",
    "active_trip_exists",
    "create_user",
    "deactivate_user",
    "get_active_trip_for_driver",
    "get_active_trip_for_manager",
    "get_all_trips",
    "get_all_users",
    "get_latest_active_trip",
    "get_trip_by_code",
    "get_trip_stats_by_code",
    "get_trips_for_user",
    "get_user_by_id",
    "get_user_by_username",
    "get_users_by_roles",
    "insert_expense",
    "insert_trip",
    "pending_expense_count",
    "reactivate_user",
    "settle_trip",
    "trip_status",
    "update_user",
]