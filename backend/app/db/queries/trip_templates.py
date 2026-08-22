"""Trip-template queries (feature F-6): reusable routes for one-tap dispatch."""
from __future__ import annotations

from typing import Any


def list_for_fleet(conn, fleet_id: int) -> list[dict[str, Any]]:
    """Return a fleet's templates newest-first with resolved labels."""
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, v.vehicle_number, u.full_name AS driver_name
             FROM trip_templates t
             LEFT JOIN vehicles v ON v.id = t.vehicle_id
             LEFT JOIN users u ON u.id = t.driver_user_id
            WHERE t.fleet_id = %s
            ORDER BY t.name""",
        (fleet_id,),
    )
    return cur.fetchall()


def insert_template(
    conn,
    fleet_id: int,
    name: str,
    vehicle_id: int | None,
    driver_user_id: int | None,
    origin: str | None,
    destination: str | None,
    created_by: int | None,
) -> int:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO trip_templates
               (fleet_id, name, vehicle_id, driver_user_id,
                origin, destination, created_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (fleet_id, name, vehicle_id, driver_user_id,
         origin, destination, created_by),
    )
    return cur.fetchone()["id"]


def delete_template(conn, template_id: int, fleet_id: int) -> bool:
    """Delete a template scoped to *fleet_id*. Returns True if a row went."""
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM trip_templates WHERE id = %s AND fleet_id = %s",
        (template_id, fleet_id),
    )
    return cur.rowcount > 0
