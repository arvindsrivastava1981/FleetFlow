from __future__ import annotations


def get_all_benchmarks(conn, user_id: int | None = None) -> list[dict]:
    """Return all fuel benchmarks ordered by state_name.

    When *user_id* is given, each row is tagged with the caller's
    ``is_favorite`` flag (their starred rows in `benchmark_favorites`) so the
    Rules & Rates page can pin favorites to the top without a second call.
    """
    cur = conn.cursor()
    if user_id is None:
        cur.execute(
            """SELECT b.*, FALSE AS is_favorite
                     FROM fuel_benchmarks b
                 ORDER BY b.state_name"""
        )
    else:
        cur.execute(
            """SELECT b.*, (bf.user_id IS NOT NULL) AS is_favorite
                     FROM fuel_benchmarks b
                LEFT JOIN benchmark_favorites bf
                       ON bf.state_code = b.state_code AND bf.user_id = %s
                 ORDER BY b.state_name""",
            (user_id,),
        )
    return cur.fetchall()


def add_benchmark_favorite(conn, user_id: int, state_code: str) -> None:
    """Star *state_code* for *user_id* (idempotent re-add is a no-op)."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO benchmark_favorites (user_id, state_code)
                VALUES (%s, %s)
           ON CONFLICT (user_id, state_code) DO NOTHING""",
        (user_id, state_code),
    )


def remove_benchmark_favorite(conn, user_id: int, state_code: str) -> bool:
    """Un-star *state_code* for *user_id*. Returns True when a row was removed."""
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM benchmark_favorites WHERE user_id = %s AND state_code = %s",
        (user_id, state_code),
    )
    return cur.rowcount > 0


def get_home_state(conn, user_id: int) -> str | None:
    """Return the caller's usual operating state (`users.home_state_code`)."""
    cur = conn.cursor()
    cur.execute("SELECT home_state_code FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    return row["home_state_code"] if row else None


def get_favorite_state_codes(conn, user_id: int) -> list[str]:
    """Return the caller's favorite state codes (their ★ rows on Rules & Rates).

    Powers the `is_favorite` flag on `GET /states` so client dropdowns (e.g. the
    driver's fueling-state picker) can pin starred states to the top.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT state_code FROM benchmark_favorites WHERE user_id = %s",
        (user_id,),
    )
    return [row["state_code"] for row in cur.fetchall()]


def get_benchmark_states(conn, user_id: int) -> list[dict]:
    """Return every state that exists in `fuel_benchmarks`, tagged with the
    caller's ``is_favorite`` flag.

    Powers the DB-driven fueling-state dropdown (`GET /states?source=benchmarks`)
    so a driver can only pick a state the rules engine can actually price.
    """
    cur = conn.cursor()
    cur.execute(
        """SELECT b.state_code,
                  b.state_name,
                  (bf.user_id IS NOT NULL) AS is_favorite
             FROM fuel_benchmarks b
        LEFT JOIN benchmark_favorites bf
               ON bf.state_code = b.state_code AND bf.user_id = %s
         ORDER BY b.state_name""",
        (user_id,),
    )
    return cur.fetchall()


def set_home_state(conn, user_id: int, state_code: str | None) -> bool:
    """Store (or clear, passing None) the caller's usual operating state."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET home_state_code = %s WHERE id = %s",
        (state_code, user_id),
    )
    return cur.rowcount > 0


def get_benchmark_price_and_tolerance(conn, state_code: str) -> tuple[float, float] | None:
    """Return ``(benchmark_price_per_liter, tolerance_pct)`` for a state, or None.

    Used by the expense route to build a per-state fuel band for the rules
    engine. `tolerance_pct` is stored as percentage points (e.g. 8.00) and is
    converted to a fraction (0.08) so it feeds `derive_band` directly.
    """
    cur = conn.cursor()
    cur.execute(
        """SELECT benchmark_price_per_liter, tolerance_pct
             FROM fuel_benchmarks WHERE state_code = %s""",
        (state_code.upper(),),
    )
    row = cur.fetchone()
    if row is None:
        return None
    tolerance_fraction = (row["tolerance_pct"] or 0.0) / 100.0
    return (float(row["benchmark_price_per_liter"]), tolerance_fraction)


def upsert_benchmarks_from_live(conn, rows: list[dict]) -> int:
    """Upsert live-scraped state prices by state_code.

    `rows` are ``{state_code, state_name, benchmark_price_per_liter}``. Existing
    rows are updated in place (the ``trg_fuel_benchmarks_updated_at`` trigger
    bumps ``updated_at``), new states are inserted with the default tolerance
    and today's effective date. Returns the number of rows touched.

    When the incoming price differs from the stored one, the old price is kept
    in `previous_price` so the Rules & Rates page can render the ▲/▼ Change
    column; an unchanged price leaves `previous_price` untouched.
    """
    cur = conn.cursor()
    touched = 0
    for row in rows:
        cur.execute(
            """INSERT INTO fuel_benchmarks
                   (state_code, state_name, benchmark_price_per_liter)
               VALUES (%s, %s, %s)
               ON CONFLICT (state_code) DO UPDATE SET
                   state_name = EXCLUDED.state_name,
                   previous_price = CASE
                       WHEN fuel_benchmarks.benchmark_price_per_liter
                            IS DISTINCT FROM EXCLUDED.benchmark_price_per_liter
                           THEN fuel_benchmarks.benchmark_price_per_liter
                       ELSE fuel_benchmarks.previous_price
                   END,
                   benchmark_price_per_liter = EXCLUDED.benchmark_price_per_liter
               """,
            (row["state_code"], row["state_name"], row["benchmark_price_per_liter"]),
        )
        touched += cur.rowcount
    return touched
