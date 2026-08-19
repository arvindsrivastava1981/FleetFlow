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