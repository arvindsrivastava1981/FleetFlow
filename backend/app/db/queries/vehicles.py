"""Query helpers for the `vehicles` table.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and return plain dict rows / booleans. None of them commit — the caller's
`get_db()` contextmanager commits on clean exit.

Scoping: `super_admin` sees every vehicle; a `trip_manager` sees only the
vehicles they registered (`created_by = user_id`). This mirrors the trip-level
ownership already used across the app.
"""
from __future__ import annotations


def _visible_clause(role: str, user_id: int | None) -> tuple[str, list]:
    """Return (SQL predicate, params) that filters vehicles by caller role.

    super_admin sees all rows; trip_manager sees only rows they created.
    """
    if role == "super_admin":
        return "TRUE", []
    return "created_by = %s", [user_id]


def get_all_vehicles(conn, role: str = "super_admin", user_id: int | None = None) -> list[dict]:
    """Return vehicles visible to the caller, newest first, with fleet owner name."""
    clause, params = _visible_clause(role, user_id)
    cur = conn.cursor()
    cur.execute(
        f"""SELECT v.*, f.owner_name AS fleet_owner
              FROM vehicles v
              LEFT JOIN fleets f ON f.id = v.fleet_id
             WHERE {clause}
             ORDER BY v.id DESC""",
        params,
    )
    return cur.fetchall()


def get_vehicle_by_id(conn, id: int, role: str = "super_admin", user_id: int | None = None) -> dict | None:
    """Return a single vehicle by ID if it is visible to the caller."""
    clause, params = _visible_clause(role, user_id)
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM vehicles WHERE id = %s AND {clause}",
        [id, *params],
    )
    return cur.fetchone()


def vehicle_number_exists(conn, vehicle_number: str, exclude_id: int | None = None) -> bool:
    """True when a vehicle with this number already exists (unique plate)."""
    cur = conn.cursor()
    if exclude_id is not None:
        cur.execute(
            "SELECT 1 FROM vehicles WHERE vehicle_number = %s AND id <> %s",
            (vehicle_number, exclude_id),
        )
    else:
        cur.execute(
            "SELECT 1 FROM vehicles WHERE vehicle_number = %s",
            (vehicle_number,),
        )
    return cur.fetchone() is not None


def insert_vehicle(
    conn,
    vehicle_number: str,
    make_model: str | None,
    tank_capacity_liters: float,
    expected_km_per_liter: float,
    owner_phone: str | None,
    created_by: int | None = None,
    fleet_id: int | None = None,
) -> int:
    """Insert a new vehicle and return its ID. *created_by* is the manager.

    *fleet_id* binds the vehicle to the fleet it belongs to (resolved from the
    creating manager's `users.fleet_id`), so it counts against the fleet's
    subscription vehicle limit.
    """
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO vehicles
               (vehicle_number, make_model, tank_capacity_liters,
                expected_km_per_liter, owner_phone, created_by, fleet_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (vehicle_number, make_model, tank_capacity_liters,
         expected_km_per_liter, owner_phone, created_by, fleet_id),
    )
    return cur.fetchone()["id"]


def update_vehicle(
    conn,
    id: int,
    vehicle_number: str,
    make_model: str | None,
    tank_capacity_liters: float,
    expected_km_per_liter: float,
    owner_phone: str | None,
) -> bool:
    """Update an existing vehicle. Returns True if a row was updated."""
    cur = conn.cursor()
    cur.execute(
        """UPDATE vehicles
              SET vehicle_number = %s, make_model = %s,
                  tank_capacity_liters = %s, expected_km_per_liter = %s,
                  owner_phone = %s
            WHERE id = %s""",
        (vehicle_number, make_model, tank_capacity_liters,
         expected_km_per_liter, owner_phone, id),
    )
    return cur.rowcount > 0


def deactivate_vehicle(conn, id: int) -> bool:
    """Soft-delete a vehicle (set is_active = FALSE). Returns True if updated."""
    cur = conn.cursor()
    cur.execute("UPDATE vehicles SET is_active = FALSE WHERE id = %s", (id,))
    return cur.rowcount > 0


def reactivate_vehicle(conn, id: int) -> bool:
    """Set is_active = TRUE for a vehicle. Returns True if updated."""
    cur = conn.cursor()
    cur.execute("UPDATE vehicles SET is_active = TRUE WHERE id = %s", (id,))
    return cur.rowcount > 0