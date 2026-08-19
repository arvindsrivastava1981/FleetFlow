"""Database connection and persistence layer.

- `connection.py` : get_db() context manager with guaranteed close,
                    DEC2FLOAT cast, fail-fast when DATABASE_URL is absent
- `queries/`      : named .py modules exposing focused SQL functions
  (trips.py, expenses.py, fleets.py, fuel_benchmarks.py, toll_corridors.py)
Zero DDL in the app; schema lives in `/database/schema.sql` only.
"""
