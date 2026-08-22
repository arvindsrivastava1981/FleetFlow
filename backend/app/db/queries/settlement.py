from __future__ import annotations


def get_settled_trips(
    conn,
    role: str = "super_admin",
    user_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Return trips with status SETTLED visible to the caller.

    trip_manager only sees trips they created; driver only their assigned ones;
    super_admin sees all. Driver info is resolved via JOIN to users.
    Rows are bounded when *limit* is given (audit R-7 pagination).
    """
    cur = conn.cursor()
    base = """
        SELECT t.*, u.full_name AS driver_name, u.phone AS driver_phone
          FROM trips t
          LEFT JOIN users u ON u.id = t.driver_user_id
    """
    order = " ORDER BY t.settled_at DESC"
    page_sql = " LIMIT %s OFFSET %s" if limit is not None else ""  # audit R-7

    if role == "trip_manager":
        where = " WHERE t.status = 'SETTLED' AND t.created_by = %s"
        params: list = [user_id]
    elif role == "driver":
        where = " WHERE t.status = 'SETTLED' AND t.driver_user_id = %s"
        params = [user_id]
    else:
        where = " WHERE t.status = 'SETTLED'"
        params = []
    if limit is not None:
        params += [limit, offset]
    cur.execute(base + where + order + page_sql, params)
    return cur.fetchall()
