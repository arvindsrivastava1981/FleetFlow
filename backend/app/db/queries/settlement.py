from __future__ import annotations


def get_settled_trips(conn, role: str = "super_admin", user_id: int | None = None) -> list[dict]:
    """Return trips with status SETTLED visible to the caller.

    trip_manager only sees trips they created; driver only their assigned ones;
    super_admin sees all. Driver info is resolved via JOIN to users.
    """
    cur = conn.cursor()
    base = """
        SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
          FROM trips t
          LEFT JOIN users u ON u.id = t.driver_user_id
    """
    if role == "trip_manager":
        cur.execute(
            base + " WHERE t.status = 'SETTLED' AND t.created_by = %s "
            "ORDER BY t.settled_at DESC",
            (user_id,),
        )
    elif role == "driver":
        cur.execute(
            base + " WHERE t.status = 'SETTLED' AND t.driver_user_id = %s "
            "ORDER BY t.settled_at DESC",
            (user_id,),
        )
    else:
        cur.execute(
            base + " WHERE t.status = 'SETTLED' ORDER BY t.settled_at DESC"
        )
    return cur.fetchall()
