from __future__ import annotations


def get_all_benchmarks(conn) -> list[dict]:
    """Return all fuel benchmarks ordered by state_name."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM fuel_benchmarks ORDER BY state_name")
    return cur.fetchall()


def get_benchmark_by_id(conn, id: int) -> dict | None:
    """Return a single fuel benchmark by ID."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM fuel_benchmarks WHERE id = %s", (id,))
    return cur.fetchone()


def insert_benchmark(conn, state_code: str, state_name: str,
                    benchmark_price_per_liter: float, tolerance_pct: float = 8.0,
                    effective_date: str | None = None) -> int:
    """Insert a new fuel benchmark and return the new ID."""
    cur = conn.cursor()
    if effective_date:
        cur.execute(
            """INSERT INTO fuel_benchmarks
               (state_code, state_name, benchmark_price_per_liter, tolerance_pct, effective_date)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (state_code, state_name, benchmark_price_per_liter, tolerance_pct, effective_date),
        )
    else:
        cur.execute(
            """INSERT INTO fuel_benchmarks
               (state_code, state_name, benchmark_price_per_liter, tolerance_pct)
               VALUES (%s, %s, %s, %s)
               RETURNING id""",
            (state_code, state_name, benchmark_price_per_liter, tolerance_pct),
        )
    return cur.fetchone()["id"]


def update_benchmark(conn, id: int, state_code: str, state_name: str,
                    benchmark_price_per_liter: float, tolerance_pct: float,
                    effective_date: str | None = None) -> bool:
    """Update an existing fuel benchmark. Returns True if updated."""
    cur = conn.cursor()
    cur.execute(
        """UPDATE fuel_benchmarks
           SET state_code = %s, state_name = %s,
               benchmark_price_per_liter = %s, tolerance_pct = %s,
               effective_date = COALESCE(%s, effective_date)
           WHERE id = %s""",
        (state_code, state_name, benchmark_price_per_liter, tolerance_pct, effective_date, id),
    )
    return cur.rowcount > 0


def delete_benchmark(conn, id: int) -> bool:
    """Delete a fuel benchmark by ID. Returns True if deleted."""
    cur = conn.cursor()
    cur.execute("DELETE FROM fuel_benchmarks WHERE id = %s", (id,))
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
                   benchmark_price_per_liter = EXCLUDED.benchmark_price_per_liter
               """,
            (row["state_code"], row["state_name"], row["benchmark_price_per_liter"]),
        )
        touched += cur.rowcount
    return touched
